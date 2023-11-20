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

func valueReceiver(f Fish) {
	f.Net = 20
	fmt.Println("Inside ValueReceiver : ", f.Net)
}
func pointerReceiver(f *Fish) {
	f.Water = 24
	fmt.Println("Inside PointerReceiver: ", f.Water)
}

func main() {
	fmt.Println()
	f1 := Fish{11, 28}
	f2 := &Fish{12, 68}

	val := []string{}
	val1 := make(map[string]int)

	valueReceiver(f1)
	fmt.Println("Outside valueRec: ", f1.Net)
	pointerReceiver(f2)
	fmt.Println("Inside PointerRec: ", f2.Water)
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
