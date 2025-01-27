// https://lars.hupel.info/topics/crdt/02-contracts/
import fc, { IPropertyWithHooks } from 'fast-check'
import { assert } from 'chai'
import { checkAll } from '../misc/fc-runner.js';

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

// partial ordering. To achieve partial ordering, the following laws must be met
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
}
const orderings: Ordering = {
  any: {
    isLeq: (x, y) => x <= y
  }
}

Promise.all([
  checkAll(contracts.partialOrdering(orderings.any, fc.integer())),
  checkAll(contracts.partialOrdering(orderings.any, fc.string())),
])