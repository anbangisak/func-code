package main

import (
	"fmt"
	"strings"
	"time"
)

func main() {
	// actStr := "PT1H5M52S"
	// actStr := "PT1H0M3.603844S"
	// actStr := "PT5M52S"
	durStr := "PT4.00S"
	durStr = strings.ReplaceAll(durStr, "PT", "")
	for _, val := range "hms" {
		durStr = strings.ReplaceAll(durStr, strings.ToUpper(string(val)), string(val))
	}
	comp, _ := time.ParseDuration(durStr)
	fmt.Println(comp)
	fmt.Println(comp.Seconds())

	// empStr := "00H00M00S"
	// // durStr := "00H00M00S"
	// empVal, _ := time.Parse("15H04M05S", empStr)
	// actStr := "PT1H5M52S"
	// PT1H0M3.603844S
	// actTimeStr := strings.ReplaceAll(actStr, "PT", "")
	// hPos := strings.Index(actStr, "H")
	// fmt.Println(hPos)
	// if hPos != -1 {
	// 	hSplitStr := strings.Split(actStr, "H")
	// 	if len(hSplitStr) > 1 {
	// 		if len(hSplitStr[0]) != 2 {
	// 			durStr = strings.ReplaceAll(durStr, "00H", "0"+hSplitStr[0]+"H")
	// 		} else {
	// 			durStr = strings.ReplaceAll(durStr, "00H", hSplitStr[0]+"H")
	// 		}
	// 	}
	// }

	// durStr := "PT01H05M52S"
	// timeStr := strings.ReplaceAll(durStr, "PT", "")
	// tval, _ := time.Parse("15H04M05S", timeStr)
	// fmt.Println(tval.Sub(empVal).Seconds())
}
