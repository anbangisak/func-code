package main

import (
	"fmt"
	"time"
)

func checkDur2Sec(dur time.Duration) {
	dispStr := fmt.Sprintf("dur: %v", dur*time.Second)
	fmt.Println(dispStr)
}

func main() {
	// checkDur2Sec(10)
	// fmt.Println("done")
	b := time.Duration(500 * time.Second).Microseconds()
	d := time.Duration(500 * time.Millisecond).Microseconds()
	a := (1 - 0.1) * float64(b)
	fmt.Println(a)
	fmt.Println(d)
}
