/*
package main

import fmt

func main() {
	ch, v := make(chan int), 1 // adding buffer will help.
	ch <- v                       //send
	v = <-ch                      //receive
	fmt.Println(v)
}

*/

package main

import "fmt"

func main() {
	ch, v := make(chan int, 1), 1 // adding buffer will help.
	ch <- v                       //send
	v = <-ch                      //receive
	fmt.Println(v)
}
