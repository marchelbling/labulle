#!/bin/sh

# from https://unix.stackexchange.com/a/162150; hook to run the script in a screen session
if [ -z "$STY" ];
then
    exec screen -U -dm -S labulle-"${1}" /bin/bash "$0" "$@";
fi

function terminate_screen {
  local session="$( screen -list | grep "${1}" | grep Detached | cut -d'.' -f1 )"
  screen -X -S ${session} quit
}
trap terminate_screen EXIT


function scrape {
    # lowercase
    local scraper="$( echo "${1}" | tr '[:upper:]' '[:lower:]' )"
    local jl="data/${scraper}/$( date +%Y-%m-%d ).jl"
    local json="data/${scraper}/$( date +%Y-%m-%d ).json"
    scrapy crawl ${scraper} -o "${jl}" >data/${scraper}/last.log 2>&1
    ./jl2json.py "${jl}" "${json}" && rm "${jl}"
    git add "${json}" && git commit -m "Update ${scraper} data" && git push origin master
}

scrape "$@"
