/**@link https://lars.hupel.info/topics/crdt/02-contracts/ */

import fc, { sample } from "fast-check";
import { assert } from 'chai'
import { checkAll } from "./misc/fc-runner.js";
import chalk from "chalk";

// Comparision is made through an operator such as '<'

const contracts = {};

// Example
// fc.property(fc.nat(), fc.string(), (maxLength, label) => {
// fc.property(...arbitraries, (...args) => {});

/**
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

const orderings = {};

// any values (partial ordering)
orderings.any = {
  isLeq: (x, y) => x <= y,
};

// # (Im)partiality
Object.defineProperty(Set.prototype, "isSubsetOf", {
  configurable: true,
  value: function (that) {
    for (const element of this.values())
      if (!that.has(element))
        return false;
    return true;
  }
});

assert.ok(new Set([1, 2]).isSubsetOf(new Set([1, 2, 3])));
assert.notOk(new Set([1, 3]).isSubsetOf(new Set([1, 2])));

// only sets (partial ordering)
orderings.set = {
  isLeq: (s1, s2) => s1.isSubsetOf(s2)
}

const smallStringGen = fc.hexaString(3);
const smallSetGen = gen => fc.array(gen, 5).map(elems => new Set(elems));

// Promise.all([
//   checkAll(contracts.partialOrdering(orderings.set, smallSetGen(fc.integer()))),
//   checkAll(contracts.partialOrdering(orderings.set, smallSetGen(smallStringGen)))
// ])

// partial ordering based on division
const divOrdering = {
  isLeq: (x, y) => {
    if (x == 0 && y == 0) return true
    const condition = y % x == 0
    if (condition) return x <= y
  }
}

checkAll(contracts.partialOrdering(divOrdering, fc.nat(10)));


const insertElement = (element, set) => new Set([...set.values(), element]);

checkAll({
  "insert-makes-bigger":
    fc.property(fc.integer(), fc.array(fc.integer()), (element, array) => {
      const set = new Set(array);
      const newSet = insertElement(element, set);
      assert.ok(orderings.set.isLeq(set, newSet));
    })
});