package main

import (
	"fmt"
)

// var wg sync.WaitGroup

func say(s string, ch chan string) {
	// defer wg.Done()
	// fmt.Println(s)
	ch <- s
}

// print hello world
func main() {
	ch := make(chan string, 2)
	// wg.Add(1)
	go say("world", ch)
	// wg.Add(1)
	say("hello", ch)
	// wg.Wait()
	fmt.Println(<-ch)
	fmt.Println(<-ch)
}

/*
package main

import "fmt"

func say(s string, ch chan int) {
	fmt.Println(s)
}

// print hello world and use channels
func main() {
	go say("world", ch)
	say("hello", ch)
}
*/
