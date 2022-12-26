package main

import "fmt"

type Fish struct {
	Net   int
	Water int
}

func (f *Fish) netMeter() {
	fmt.Println(f.Net)
	fmt.Println(f.Water)
}

func main() {
	fmt.Println()
	f := Fish{
		Net:   10,
		Water: 10,
	}
	pt := &f
	fmt.Println(*pt)
	fmt.Println((*pt).Net)
	(*pt).netMeter()
	fmt.Println((*pt).Water)
}
