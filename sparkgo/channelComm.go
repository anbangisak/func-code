package main

import (
	"fmt"
	"sync"
	"time"
)

var wg sync.WaitGroup
var line chan int

func lineSender(rangeVal int) {
	defer wg.Done()
	for i := 0; i < rangeVal; i++ {
		line <- i
	}
}

func lineRec(rangeVal int) {
	defer wg.Done()
	for i := 0; i < rangeVal; i++ {
		time.Sleep(time.Duration(100) * time.Millisecond)
		fmt.Println("val: ", <-line)
	}
}

func main() {
	fmt.Println()
	rangeVal := 100
	line = make(chan int)
	wg.Add(1)
	go lineSender(rangeVal)
	// first way
	// wg.Add(1)
	// go lineRec(rangeVal)
	// wg.Wait()

	// 2nd way
	for i := 0; i < rangeVal; i++ {
		time.Sleep(time.Duration(100) * time.Millisecond)
		fmt.Println("val: ", <-line)
	}

}
