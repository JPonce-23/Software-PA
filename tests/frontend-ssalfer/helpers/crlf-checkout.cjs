// Preload for the Windows regression run: simulate CRLF application sources
// without rewriting the checkout. Historical `git show` output remains LF.
const fs = require('node:fs');
const path = require('node:path');
const originalRead = fs.readFileSync;
const sourceRoot = path.resolve(__dirname, '../../../frontend-ssalfer/js') + path.sep;
fs.readFileSync = function (file, ...options) {
    const value = originalRead.call(this, file, ...options);
    if (typeof file === 'string' && path.resolve(file).startsWith(sourceRoot) &&
        file.endsWith('.js') && typeof value === 'string') {
        return value.replace(/\r\n?/g, '\n').replace(/\n/g, '\r\n');
    }
    return value;
};
