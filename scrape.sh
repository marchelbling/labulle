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
    # lowercase
    local scraper="$( echo "${1}" | tr '[:upper:]' '[:lower:]' )"

    # clean data
    rm -fr "data/${scraper}"
    mkdir -p "data/${scraper}"

    # scrape
    scrapy crawl ${scraper} -t jl -o "data/${scraper}/jl" >>data/${scraper}/log 2>&1

    # build diff
    ./algdiff.py --data "data/${scraper}/jl" >data/${scraper}/diff 2>>data/${scraper}/err

    # fetch cover/samples
    ./dlsamples.py "data/${scraper}/diff"

    # # enrich records from images
    # ./enrich.py "data/${scraper}/diff"

    #  upload enriched diff
    # ./algupload.py --data "data/${scraper}/jl" >>data/${scraper}/log 2>>data/${scraper}/err

    # commit data
    # git add "data/${scraper}/*" && git commit -m "update ${scraper} data" && git push origin master
}

scrape "$@"
