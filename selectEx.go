package main

import (
	"fmt"
	"sync"
	"time"
)

var wg sync.WaitGroup

func disp(ch chan string, strArr []string, dur int) {
	defer wg.Done()
	for _, str := range strArr {
		time.Sleep(time.Duration(dur) * time.Millisecond)
		ch <- str
	}
}

func main() {
	fmt.Println()
	ch1 := make(chan string)
	ch2 := make(chan string)
	strArr1 := [3]string{"hi", "hai", "fresh"}
	strArr2 := [3]string{"mi", "mai", "mresh"}
	wg.Add(1)
	go disp(ch1, strArr1[:], 10)
	wg.Add(1)
	go disp(ch2, strArr2[:], 20)

	for i := 0; i < len(strArr1)+len(strArr2); i++ {
		time.Sleep(time.Duration(100) * time.Millisecond)
		select {
		case val := <-ch1:
			fmt.Println("ch1: ", val)
		case val2 := <-ch2:
			fmt.Println("ch2: ", val2)
		}
	}

	close(ch1)
	close(ch2)
}
