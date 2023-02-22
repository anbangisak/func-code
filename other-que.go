// behavioural design pattern.
package main

import "fmt" // DanceOn Interface Defined

type DanceOn interface {
	Dance()
} // BreakDance Struct Defined
type BreakDance struct {
	Name string
} // AerialDance Struct Defined
type AerialDance struct {
	Name string
} // Dance Function implemented from DanceOn Interface

func (b BreakDance) Dance() {
	fmt.Printf("%s is doing Breakdance on the floor\n", b.Name)
} // Dance Function implemented from DanceOn Interface
func (a AerialDance) Dance() {
	fmt.Printf("%s is doing Aerialdance on the air\n", a.Name)
}

func main() {
	var breakdancer BreakDance
	breakdancer.Name = "Michael Jackson"
	breakdancer.Dance()
	var aerialdancer AerialDance
	aerialdancer.Name = "Kal"
	aerialdancer.Dance()
}
