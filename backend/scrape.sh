#!/bin/bash -e

# from https://unix.stackexchange.com/a/162150; hook to run the script in a screen session
if [ -z "$STY" ];
then
    [ -n "$1" ] || ( echo "cannot use empty name"; exit 1 )
    exec screen -U -dm -S labulle-"${1}" /bin/bash "$0" "$@";
fi

function terminate_screen {
  local session="$( screen -list | grep "${1}" | grep Detached | cut -d'.' -f1 )"
  screen -X -S ${session} quit
}
trap terminate_screen EXIT


function scrape {
    # lowercase input for resiliency
    local scraper="$( echo "${1}" | tr '[:upper:]' '[:lower:]' )"

    # source env
    local root="$( git rev-parse --show-toplevel 2> /dev/null )"
    [ -f "${root}/.env" ] && . "${root}/.env" || echo "No ${root}/.env to source"

    # fs layout
    local scripts="${root}/backend/scripts"
    local images="${root}/data/img"
    local records="${root}/data/records/${scraper}"

    local comics="${records}/jl"
    local diff="${records}/diff"
    local log="${records}/log"
    local err="${records}/err"

    mkdir -p "${records}"

    # scrape
    scrapy crawl ${scraper} -t jl -o "${comics}" >>"${log}" 2>&1

    # build diff
    # use diff=${comics} to perform a full dlsamples/algupload
    ./${scripts}/algdiff.py --data "${comics}" >"${diff}" 2>>"${err}"

    # fetch cover/samples
    ./${scripts}/dlsamples.py "${diff}" "${images}"

     # upload diff
    ./${scripts}/algupload.py --data "${diff}" >>"${log}" 2>>"${err}"

    # commit data
    git add "${folder}" && git commit -m "update ${scraper} data" && git push origin master
}

scrape "$@"
