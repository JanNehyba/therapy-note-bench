// A DOM small enough to run the page's script and loud enough to notice when it
// throws. Not a browser: it checks that every render function executes over the
// real data, which is the failure a syntax check cannot see.
const fs = require('fs');
const path = process.argv[2];

class El {
  constructor(tag) { this.tag = tag; this.children = []; this._html = ''; this.dataset = {};
                     this.style = {}; this.classList = { add(){}, remove(){}, contains(){return false} }; }
  set innerHTML(v) { this._html = String(v); }
  get innerHTML() { return this._html; }
  set textContent(v) { this._text = String(v); }
  get textContent() { return this._text || ''; }
  addEventListener() {}
  querySelector() { return new El('div'); }
  querySelectorAll() { return []; }
  appendChild(c) { this.children.push(c); return c; }
  remove() { this.removed = true; }
  closest() { return new El('table'); }
  getAttribute() { return null; }
  setAttribute() {}
}

const nodes = {};
global.document = {
  getElementById(id) { return (nodes[id] = nodes[id] || new El('div')); },
  querySelectorAll() { return []; },
  createElement(tag) { return new El(tag); },
  addEventListener() {},
  body: new El('body'),
  // The language switch stamps the chosen language on the root element.
  documentElement: new El('html'),
};
// Before the script runs, not after: the leaderboard reads `location.hash` to
// decide which table to draw, and a missing stub throws on the first line of
// every page test at once rather than in the one that cares.
// `PAGE_SEARCH=?lang=cs` runs the page in the other language: the switch
// reads it there, and a render function that throws only in Czech is a
// render function that throws.
// What the page did to the address, recorded rather than discarded. Opening
// the site used to rewrite a clean URL to `#tneval-soap-<judge>-...` before the
// reader had touched anything, and nothing here could see it: `hash` was a
// plain property and `replaceState` a no-op, so both writes vanished.
global.__address = { hashSets: [], replaced: [], pushed: [] };
global.location = {
  href: 'https://example.invalid/',
  pathname: '/',
  search: process.env.PAGE_SEARCH || '',
  _hash: process.env.PAGE_HASH || '',
  get hash() { return this._hash; },
  set hash(value) { this._hash = value; global.__address.hashSets.push(value); },
};
global.history = {
  replaceState(_state, _title, url) { global.__address.replaced.push(url); },
  pushState(_state, _title, url) { global.__address.pushed.push(url); },
};
global.window = {
  addEventListener() {},
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  location: global.location,
  history: global.history,
};
global.localStorage = { getItem() { return null; }, setItem() {} };

let threw = false;
try {
  new Function(fs.readFileSync(path, 'utf8'))();
} catch (error) {
  console.log('THREW: ' + error.message);
  console.log(error.stack.split('\n').slice(0, 4).join('\n'));
  // The exit code, not `process.exit`: see the note below on why nothing here
  // exits after printing.
  process.exitCode = 1;
  threw = true;
}

// With a second argument, print that panel's rendered HTML instead of the
// summary: a string can sit in the template unconditionally and still never
// reach the page, so asserting on the source cannot tell the two apart.
const wanted = process.argv[3];
// `--all` prints every node the page wrote into, which is what an audit of the
// published figures needs: naming the panels one by one is a list that goes
// stale the first time somebody adds a section, and going stale silently is
// the failure such an audit exists to prevent.
//
// **No `process.exit` after a print.** On Windows a write to a pipe is
// synchronous and on Linux it is not, so `console.log(big); process.exit(0)`
// hands back whatever happened to have been flushed -- the rest is dropped
// with the process. Every panel here is tens of kilobytes, so on Linux the
// tail went missing and the tests reading it saw a page that stopped
// mid-element: two of them failed on the published pages for a week, on
// Linux only, reporting that a clause was "not drawn" and a figure "not on the
// page" when both were simply past the cut. Node exits on its own when there
// is nothing left to do, and it flushes on the way out.
if (threw) {
  // Nothing more to say: the page did not run, and whatever was drawn before
  // it stopped is not a page anybody should assert on.
} else if (wanted === '--all') {
  console.log(Object.entries(nodes).map(([id, el]) =>
    '<!-- node ' + id + ' -->' + (el.innerHTML || '')).join(''));
} else if (wanted) {
  console.log(nodes[wanted] ? nodes[wanted].innerHTML : '(panel absent)');
} else {
  summary();
}

function summary() {
const rendered = Object.entries(nodes)
  .filter(([, el]) => el.innerHTML && el.innerHTML.length > 40)
  .map(([id, el]) => `${id}: ${el.innerHTML.length} chars`);
console.log('RAN. panels rendered:');
rendered.forEach(line => console.log('  ' + line));
// Removal is a render decision like any other -- a page may take out
// the paragraph linking a methods page that is not beside it -- and a node
// that is gone is indistinguishable from one that was never asked for
// unless the runner says so. Printed BEFORE the empty list: three tests read
// everything after that marker and would see this line as an empty panel.
const gone = Object.entries(nodes).filter(([, el]) => el.removed).map(([id]) => id);
if (gone.length) console.log('removed: ' + gone.join(', '));
const empty = Object.entries(nodes).filter(([, el]) => !el.innerHTML && !el.removed).map(([id]) => id);
if (empty.length) console.log('empty and not removed: ' + empty.join(', '));
}
