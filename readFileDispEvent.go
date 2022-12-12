package main

import (
	"bufio"
	"fmt"
	"log"
	"os"
	"strings"
)

func main() {
	// fmt.Println("hai")
	fileObj, err := os.Open("FS2HD_mpd_events.txt")
	if err != nil {
		log.Fatal("unable to read file")
	}
	defer fileObj.Close()

	scanObj := bufio.NewScanner(fileObj)
	count := 0
	for scanObj.Scan() {
		strObj := scanObj.Text()
		if strings.Contains(strObj, "2022/09/29") {
			fmt.Println("event count: ", count)
			count = 0
		}
		if strings.Contains(strObj, "Event") {
			count += 1
		}
	}

	if err := scanObj.Err(); err != nil {
		log.Fatal(err)
	}
}
