// You can edit this code!
// Click here and start typing.
package main

import (
	"fmt"
	"time"
)

func main() {
	fmt.Println("Hello, 世界")
	when := time.Now().UTC()
	targetExecTime := when.Add(time.Duration(20) * time.Millisecond)
	fmt.Println("when: ", when)
	fmt.Println("targetExecTime: ", targetExecTime)
	fmt.Println("after ", targetExecTime.After(when))
	if targetExecTime.After(when) {
		fmt.Println(time.Now().UTC())
	}
}
