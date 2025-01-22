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

function openOrSenior(data){ 
  const result = []
  for (let i = 0; i < data.length; i++){
    const age = data[i][0]
    const handicap = data[i][1]
    if(age >= 55 && handicap > 7) {
      result.push('Senior')
    }else{
      result.push('Open')
    }
  }

  console.log(result)
  return result
}

openOrSenior([[3, 12],[55,1],[91, -2],[53, 23]])