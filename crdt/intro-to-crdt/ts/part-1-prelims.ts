// https://lars.hupel.info/topics/crdt/01-intro/
import { checkAll } from '../misc/fc-runner.js'
import fc from 'fast-check'
import { assert } from 'chai'

// fc.string() will be pass to the predicate, in this case it's x
checkAll({
  "succeed": fc.property(fc.string(), x => x == x), // string will always be equal to itself
  "fail": fc.property(fc.string(), x => x != x) // string will never be equal to itself
});

// using chai instead of normal JS operator
checkAll({
  "succeed": fc.property(fc.string(), x => assert.equal(x, x)),
  "fail": fc.property(fc.string(), x => assert.notEqual(x, x))
});

checkAll({
  "strlen": fc.property(fc.string(), x => assert.isAtMost(x.trim().length, 5))
});

// fc has a check for incoming values: fc.check
checkAll({
  "be-creative": null
});