// function reverseArray(a: number[]): number[] {
//   // Write your code here
//   const b: number[] = []
//   for (let i = a.length - 1; i >= 0; i--) {
//     b.push(a[i])
//   }
//   return b
// }

// console.log(reverseArray([1, 2, 3]))

// function hourglassSum(arr: number[][]): number {
//   let sumArr = []

//   for (let i = 0; i < 4; i++) {
//     for (let j = 0; j < 4; j++) {
//       let sum = 
//         arr[i][j] + arr[i][j + 1] + arr[i][j + 2] + 
//         arr[i + 1][j + 1] + 
//         arr[i + 2][j] + arr[i + 2][j + 1] + arr[i + 2][j + 2]
//       // console.log(arr[i][j], arr[i][j+1], arr[i][j+2])
//       // console.log(" ", arr[i+1][j+1], " ")
//       // console.log(arr[i+2][j], arr[i+2][j+1], arr[i+2][j+2])

//       sumArr.push(sum)
//     }
//   }
//   console.log(sumArr)

//   return Math.max(...sumArr)

// }

// // sum = 28
// // 16 hourglasses
// hourglassSum(
//   [
//     [-9, -9, -9, 1, 1, 1],
//     [0, -9, 0, 4, 3, 2],
//     [-9, -9, -9, 1, 2, 3],
//     [0, 0, 8, 6, 6, 0],
//     [0, 0, 0, -2, 0, 0],
//     [0, 0, 1, 2, 4, 0]
//   ]
// )

// function openOrSenior(data){ 
//   const result = []
//   for (let i = 0; i < data.length; i++){
//     const age = data[i][0]
//     const handicap = data[i][1]
//     if(age >= 55 && handicap > 7) {
//       result.push('Senior')
//     }else{
//       result.push('Open')
//     }
//   }

//   console.log(result)
//   return result
// }

// openOrSenior([[3, 12],[55,1],[91, -2],[53, 23]])

// function descendingOrder(n: number) {
//   const findLargest = (arr: number[]) => {
//     let largest = arr[0]
//     let largestIndex = 0

//     arr.forEach((item, index) => {
//       if (item > largest) {
//         largest = item
//         largestIndex = index
//       }
//     })
//     return { largestIndex }
//   }

//   const isOneDigit = n < 10
//   if (isOneDigit) {
//     return n
//   } else {
//     const arrN = n.toString().split("").map(Number)
//     const result: string[] = []
//     while (arrN.length > 0) {
//       const { largestIndex } = findLargest(arrN)
//       result.push(arrN[largestIndex].toString()) 
//       arrN.splice(largestIndex, 1)
//     }
//     return Number(result.join(''))
//   }
// }
// descendingOrder(1021)

function sevenAte9(str) {
  const strArr = str.split('')
  const removeIndex: number[] = []
  let result: number[] = []

  for (let i = 1; i < strArr.length; i++) {
    const lookahead = strArr[i + 1]
    const lookbehind = strArr[i - 1]
    const current = strArr[i]

    if (current === '9') {
      if (lookahead === '7' && lookbehind === '7') {
        removeIndex.push(i)
      }
    }
  }

  strArr.forEach((item, index) => {
    if (!removeIndex.includes(index)) {
      result.push(item)
    }
  })
  return result.join('')

}

// Actual ANS
// function sevenAte9(str){
//   return str.replace(/79(?=7)/g, '7');
// }
sevenAte9('797')
sevenAte9('7979797')
sevenAte9('165561786121789797')