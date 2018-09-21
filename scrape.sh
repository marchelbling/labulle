#!/bin/bash -e

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
    pip3 install -r requirements.txt

    # lowercase
    local scraper="$( echo "${1}" | tr '[:upper:]' '[:lower:]' )"
    local jl="data/${scraper}.jl"

    # scrape
    scrapy crawl ${scraper} -o "${jl}" >data/${scraper}.log 2>&1

    # build & upload diff
    ./algdiff.py --app "IQKQPU4IQQ" --index "labulle" --key "${API_KEY}" --data "${jl}" >data/${scraper}.diff 2>data/${scraper}.err

    # commit data
    git add "data/${scraper}.*" && git commit -m "update ${scraper} data" && git push origin master
}

scrape "$@"
