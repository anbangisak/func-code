package main

import (
	"fmt"
	"time"

	"github.com/senseyeio/duration"
)

func main() {
	d, _ := duration.ParseISO8601("PT5M52S")
	// d, _ := iso8601.ParseISO8601("PT5M52S")
	fmt.Println(d.TH, d.TM, d.TS, d.M, d.Y, d.W)
	currentTime := time.Now()
	fmt.Println(currentTime)
	shiftTime := d.Shift(currentTime)
	fmt.Println(shiftTime.Sub(currentTime).Seconds())
	fmt.Println(shiftTime)
	// d.Shift()
	fmt.Println(d)
}
