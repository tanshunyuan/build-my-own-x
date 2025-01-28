// https://lars.hupel.info/topics/crdt/02-contracts/
import fc, { Arbitrary, IPropertyWithHooks, sample } from 'fast-check'
import { assert } from 'chai'
import { checkAll } from '../misc/fc-runner.js';

const cl = (...items: any) => console.log(...items)

// <= means less than or equal to

type Comparator<XType = any, YType = any> = {
  isLeq: (x: XType, y: YType) => boolean
}


// Sets are often used in partial ordering, however in JS it can't be directly compared like so
// Set({1,2}) <= Set({1,3}) OR Set({1,3}) <= Set({1,2}). Both are not valid syntaxes. So we need to create
// our own comparator 

const numberComparator: Comparator<number, number> = {
  isLeq: (x, y) => x <= y
};

const stringComparator: Comparator<string, string> = {
  isLeq: (x, y) => x <= y
};

// the top comparator can be combined into
const anyComparator: Comparator = {
  isLeq: (x: any, y: any) => x <= y
}

// partial ordering (contract). To achieve partial ordering, the following laws (constraints) must be met
// - reflexitivity: any value must be <= to itself
// - transtivity: given any three value: x,y and z. z <= y, y <= z and x <= y
// - antisymettry 

// contract is a behaviour rule, and partial ordering is the constraint we want the comparators to statisfy
type PartialOrdering = (instance: Comparator, gen: fc.Arbitrary<any>) => { refl: fc.IPropertyWithHooks<any>, trans: IPropertyWithHooks<any> }

type Contract = {
  partialOrdering?: PartialOrdering
}
const contracts: Contract = {}

contracts.partialOrdering = (instance, gen) => ({
  refl: fc.property(gen, x => assert.ok(instance.isLeq(x, x))),
  trans: fc.property(gen, gen, gen, (x, y, z) => {
    // fc.pre is precondition, if it fails, it'll attempt to regenerate input till it hits true
    fc.pre(instance.isLeq(x, y))
    fc.pre(instance.isLeq(y, z))
    assert.ok(instance.isLeq(x, z))
  })
})

type Ordering = {
  any: Comparator
  set: Comparator<Set<number | string>>
}
const orderings: Ordering = {
  any: {
    isLeq: (x, y) => x <= y
  },
  set: {
    isLeq: (x, y) => x.isSubsetOf(y)
  }
}

// Promise.all([
//   checkAll(contracts.partialOrdering(orderings.any, fc.integer())),
//   checkAll(contracts.partialOrdering(orderings.any, fc.string())),
// ])

// for implementation we can use chai's deepEqual to ensure both Sets are equal
assert.deepEqual(new Set([1, 2]), new Set([1, 2]));

// defining a '<=' equivalent for Set
declare global {
  interface Set<T> {
    isSubsetOf(rOperand: Set<T>): boolean
  }
}

Object.defineProperty(Set.prototype, 'isSubsetOf', {
  configurable: true,
  value: function (rOperand) {
    const lOperand = this.values()
    for (const element of lOperand) {
      if (!rOperand.has(element)) {
        return false
      }
    }
    return true
  }
})

assert.ok(new Set([1, 2]).isSubsetOf(new Set([1, 2, 3])));
assert.notOk(new Set([1, 3]).isSubsetOf(new Set([1, 2])));

/**
 * @returns Array of Sets with elements passed in from the generator
 */
const smallSetGen = (gen: Arbitrary<number | string>) => fc.array(gen, { maxLength: 5 }).map(elements => {
  // { elements: [ -154212869, 123330876 ] }
  return new Set(elements)
})


Promise.all([
  checkAll(contracts.partialOrdering(orderings.set, smallSetGen(fc.integer()))),
  checkAll(contracts.partialOrdering(orderings.set, smallSetGen(fc.hexaString({ maxLength: 3 }))))
])