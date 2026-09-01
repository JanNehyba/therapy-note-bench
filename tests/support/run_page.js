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
global.location = {
  hash: '', href: 'https://example.invalid/', search: process.env.PAGE_SEARCH || '',
};
global.history = { replaceState() {}, pushState() {} };
global.window = {
  addEventListener() {},
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  location: global.location,
  history: global.history,
};
global.localStorage = { getItem() { return null; }, setItem() {} };

try {
  new Function(fs.readFileSync(path, 'utf8'))();
} catch (error) {
  console.log('THREW: ' + error.message);
  console.log(error.stack.split('\n').slice(0, 4).join('\n'));
  process.exit(1);
}

// With a second argument, print that panel's rendered HTML instead of the
// summary: a string can sit in the template unconditionally and still never
// reach the page, so asserting on the source cannot tell the two apart.
const wanted = process.argv[3];
if (wanted) {
  console.log(nodes[wanted] ? nodes[wanted].innerHTML : '(panel absent)');
  process.exit(0);
}

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
