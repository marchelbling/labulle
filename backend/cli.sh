#!/bin/bash -e

readonly root="$( git rev-parse --show-toplevel 2> /dev/null )"
readonly scripts="${root}/backend/scripts"
readonly screen_name="labulle-backend"

# from https://unix.stackexchange.com/a/162150; hook to run the script in a screen session
if [ -z "$STY" ];
then
    exec screen -U -dm -S "${screen_name}" /bin/bash "$0" "$@";
fi

function terminate_screen {
  local session="$( screen -list | grep "${screen_name}" | grep Detached | cut -d'.' -f1 )"
  screen -X -S ${session} quit
}
trap terminate_screen EXIT


function parse_actions {
    readonly all_actions=("scrape" "diff" "download" "update" "commit")
    actions=()

    for input in  "$@";
    do
        case ${input} in
            scrape|diff|download|update|commit)
                actions+=("${input}")
                shift 1
            ;;
            deploy)
                actions="${all_actions[@]}"
                break
            ;;
        esac
    done

    if [ ${#actions[@]} == 0 ]
    then
        echo "Missing action. Choose any action or list of actions in: ${all_actions[@]}"
        exit 1
    fi

    echo "actions: ${actions[@]}"
}


function parse_editors {
    get_all_editors
    editors=()

    for input in "$@";
    do
        if grep "${input}" <<<"${all_editors[@]}";
        then
            editors+=("${input}")
        fi
    done

    if [ ${#editors[@]} == 0 ]
    then
        editors="${all_editors[@]}"
    fi

    echo "editors: ${editors[@]}"
}


function get_all_editors {
    all_editors=()
    while read scraper;
    do
        local editor="$( basename "${scraper%.*}" )"
        if [ "${editor}" != "__init__" ]
        then
            all_editors+=("${editor}")
        fi
    done<<<$( find ${root}/backend/labulle/spiders/ -mindepth 1 -maxdepth 1 -type f  )
}


function set_env {
    local editor="$1"

    # source env
    [ -f "${root}/.env" ] && . "${root}/.env" || echo "No ${root}/.env to source"

    # fs layout
    images="${root}/data/img"
    records="${root}/data/records/${editor}"

    # defaults
    comics="${records}/jl"
    diff="${records}/diff"

    # logging
    log="${records}/log"
    err="${records}/err"
    [ -f "${log}" ] && >"${log}"
    [ -f "${err}" ] && >"${err}"

    mkdir -p "${records}" "${images}"
}


function scrape {
    ( cd "${root}/backend/labulle" && scrapy crawl ${editor} -t jl -o "${comics}" >>"${log}" 2>&1 )
}


function diff {
    local from="${1:-"${comics}"}"
    local to="${2:-"${diff}"}"

    # use diff=${comics} to perform a full dlsamples/algupload
    ./${scripts}/algdiff.py --data "${from}" >"${to}" 2>>"${err}"
}


function download {
    local from="${1:-"${diff}"}"
    local to="${2:-"${images}"}"

    # fetch cover/samples
    ./${scripts}/dlsamples.py "${from}" "${to}"
}


function update {
    local from="${1:-"${diff}"}"

    # upload diff
   ./${scripts}/algupload.py --data "${from}" >>"${log}" 2>>"${err}"
}


function commit {
    # commit data
    git add "${folder}" && git commit -m "update ${scraper} data" && git push origin master
}


function execute {
    for editor in ${editors[@]};
    do
        set_env "${editor}"
        for action in ${actions[@]};
        do
            echo "[$( date -u +%Y-%m-%dT%H:%M:%S )] performing '${action}' for editor ${editor}" >>"${log}"
            ${action}
        done
    done
}


if [ $# -gt 0 ];
then
    parse_editors "$@"
    parse_actions "$@"
    execute
fi
