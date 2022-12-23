package main

import "fmt"

func main() {
	fmt.Println()
	king := 1
	val := func() int {
		king += 1
		return king
	}
	fmt.Println(val())
}
