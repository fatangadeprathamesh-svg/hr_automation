import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const parser = await import(pathToFileURL(path.join(__dirname, 'node_modules/@babel/parser/lib/index.js')).href);
const traverseMod = await import(pathToFileURL(path.join(__dirname, 'node_modules/@babel/traverse/lib/index.js')).href);
const traverse = traverseMod.default?.default || traverseMod.default;

const KNOWN_GLOBALS = new Set([
  'window', 'document', 'navigator', 'location', 'history', 'console',
  'fetch', 'localStorage', 'sessionStorage', 'setTimeout', 'setInterval',
  'clearTimeout', 'clearInterval', 'requestAnimationFrame', 'cancelAnimationFrame',
  'Date', 'Math', 'JSON', 'Promise', 'URL', 'URLSearchParams', 'FormData',
  'FileReader', 'Blob', 'File', 'encodeURIComponent', 'decodeURIComponent',
  'Boolean', 'Array', 'Object', 'Number', 'String', 'Error', 'TypeError',
  'RangeError', 'ReferenceError', 'SyntaxError', 'Set', 'Map', 'WeakMap',
  'WeakSet', 'Intl', 'RegExp', 'Infinity', 'NaN', 'undefined', 'null',
  'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'import', 'process', 'globalThis',
  'alert', 'CustomEvent', 'confirm', 'prompt'
]);

function getAllFiles(dir, exts = ['.js', '.jsx']) {
  let results = [];
  const list = fs.readdirSync(dir);
  list.forEach((file) => {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat && stat.isDirectory()) {
      results = results.concat(getAllFiles(fullPath, exts));
    } else {
      if (exts.includes(path.extname(file))) {
        results.push(fullPath);
      }
    }
  });
  return results;
}

const srcDir = path.join(__dirname, 'src');
const files = getAllFiles(srcDir);
const issues = [];

for (const filePath of files) {
  const code = fs.readFileSync(filePath, 'utf-8');
  try {
    const ast = parser.parse(code, {
      sourceType: 'module',
      plugins: ['jsx', 'typescript'],
    });

    traverse(ast, {
      ReferencedIdentifier(identPath) {
        const name = identPath.node.name;
        if (KNOWN_GLOBALS.has(name)) return;
        if (identPath.scope.hasBinding(name)) return;

        // Skip JSX tags (handled by React or components)
        if (identPath.parentPath.isJSXOpeningElement() || identPath.parentPath.isJSXClosingElement()) {
          if (/^[a-z]/.test(name)) return;
        }

        // Skip member expression properties (e.g. obj.name)
        if (identPath.parentPath.isMemberExpression() && identPath.parentPath.node.property === identPath.node && !identPath.parentPath.node.computed) {
          return;
        }

        issues.push({
          file: path.relative(path.join(__dirname, '..'), filePath),
          line: identPath.node.loc?.start?.line,
          name: name,
        });
      },
    });
  } catch (err) {
    console.error(`Error parsing ${filePath}:`, err.message);
  }
}

console.log('Undefined reference scan complete.');
if (issues.length === 0) {
  console.log('✓ No undefined references found in frontend/src!');
} else {
  console.log(`Found ${issues.length} potential undefined references:`);
  console.table(issues);
}
