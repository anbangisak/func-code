package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
)

func ListOddOrEven(rangeVal int) {
	for idx := 0; idx < rangeVal; idx++ {
		if idx%2 == 0 {
			fmt.Println("given value is even ", idx)
		} else {
			fmt.Println("value is odd ", idx)
		}
	}
}

func main() {
	reader := bufio.NewReader(os.Stdin)
	fmt.Println("enter range number: ")
	valStr, err := reader.ReadString('\n')
	if err != nil {
		fmt.Println("unable to read string from CLI ", err)
	}
	valStr = strings.Replace(valStr, "\r\n", "", -1)
	value, err := strconv.Atoi(valStr)
	if err != nil {
		fmt.Println("unable to parse given string ", err)
	}
	ListOddOrEven(value)
}
