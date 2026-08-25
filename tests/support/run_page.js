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
};
global.window = { addEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {} }) };
global.localStorage = { getItem() { return null; }, setItem() {} };

try {
  new Function(fs.readFileSync(path, 'utf8'))();
} catch (error) {
  console.log('THREW: ' + error.message);
  console.log(error.stack.split('\n').slice(0, 4).join('\n'));
  process.exit(1);
}

const rendered = Object.entries(nodes)
  .filter(([, el]) => el.innerHTML && el.innerHTML.length > 40)
  .map(([id, el]) => `${id}: ${el.innerHTML.length} chars`);
console.log('RAN. panels rendered:');
rendered.forEach(line => console.log('  ' + line));
const empty = Object.entries(nodes).filter(([, el]) => !el.innerHTML && !el.removed).map(([id]) => id);
if (empty.length) console.log('empty and not removed: ' + empty.join(', '));
