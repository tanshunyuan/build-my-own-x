// https://github.dev/larsrh/website/blob/c313c851e7def3175a4098f917e291f342225b4a/js/topics/crdt/fc-runner.js
import fc from 'fast-check'
import chalk from 'chalk' // For colored console output

const trimMax = (str, len) => {
  if (str.length > len)
    return str.substr(0, len) + " ...";
  else
    return str;
}

const success = numRuns => ({
  status: chalk.green('Success'),
  message: `${numRuns} inputs tested`
});

const failure = (error, counterexample) => {
  const result = {
    status: chalk.red('Failure'),
    message: trimMax(error || "", 50)
  };
  
  if (counterexample) {
    result.counterexample = counterexample;
  }
  
  return result;
}

const processResult = ({ failed, numRuns, error, counterexample }) => {
  if (failed)
    return failure(error, counterexample);
  else
    return success(numRuns);
}

const printResult = (key, result) => {
  console.log(`\n${chalk.bold(key)}:`);
  console.log(`Status: ${result.status}`);
  console.log(`Message: ${result.message}`);
  if (result.counterexample) {
    console.log('\nCounterexample:');
    console.log(JSON.stringify(result.counterexample, null, 2));
  }
}

const checkAll = async props => {
  const results = await Promise.all(
    Object.entries(props).map(async ([key, value]) => {
      const result = processResult(await Promise.resolve(fc.check(value)));
      printResult(key, result);
      return [key, result];
    })
  );
  return Object.fromEntries(results);
};

export {
  checkAll
}