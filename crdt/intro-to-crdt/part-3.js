// https://lars.hupel.info/topics/crdt/03-lattices/

import { assert } from "chai"
import { checkAll } from './misc/fc-runner.js'
import fc from 'fast-check'

const lattices = {}
const contracts = {}

/**
 * FROM part-2
 * @description partialOrdering
 * partial - only a subset of values can be matched hence partial
 * ordering - the sequential order of values
 * items must be reflexive & transitive
 */
contracts.partialOrdering = (instance, gen) => ({
  /**@description reflexivity: the value must be less than or equals to itself*/
  refl: fc.property(gen, (x) => assert.ok(instance.isLeq(x, x))),
  /**@description transitivity: the three values must be, x <= y, y<=z & x <= z */
  trans: fc.property(gen, gen, gen, (x, y, z) => {
    fc.pre(instance.isLeq(x, y));
    fc.pre(instance.isLeq(y, z));
    assert.ok(instance.isLeq(x, z));
  }),
});

/**@description a named function creating a set */
const set = (...elems) => new Set(elems);
const cl = (...items) => console.log(...items)

const S1 = set(1).union(set(2))
const S2 = set(1,2)

cl(assert.deepEqual(S1, S2))

lattices.set = {
  /**
   * @param {Set} x 
   * @param {Set} y 
   * @returns 
   */
  join: (x, y) => x.union(y)
}

/**
 * 
 * @param {lattice.set} instance 
 * @param {*} gen 
 * @returns 
 */
contracts.lattice = (instance, gen) => ({
  assoc: fc.property(gen, gen, gen, (x,y,z) => {
    const x_yz = instance.join(x, instance.join(y, z));
    const xy_z = instance.join(instance.join(x, y), z)
    assert.deepEqual(x_yz, xy_z)
  }),
  commute: fc.property(gen, gen, (x, y) => {
    const xy = instance.join(x,y)
    const yx = instance.join(y,x)
    assert.deepEqual(xy, yx)
  }),
  idem: fc.property(gen, x => {
    const xx = instance.join(x, x);
    assert.deepEqual(xx, x);
  })
})

const intSetGen = fc.array(fc.integer()).map(entries => set(entries));

checkAll(contracts.lattice(lattices.set, intSetGen));

// if the union of x & y is equals to y, we can say that x is less than y
// x = {1, 2}; y = {1, 2, 3}; union of x v y = {1,2,3}; x < y = {1,2} < {1,2,3}
const partialOrderingOfLattice = lattice => ({
  isLeq: (x, y) => assert.deepEqual(lattice.join(x, y), y)
});

const smallSetGen = gen => fc.array(gen, 5).map(elems => set(elems));

checkAll(
  contracts.partialOrdering(
    partialOrderingOfLattice(lattices.set),
    smallSetGen(fc.integer())
  )
);