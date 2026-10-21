// Normalize checkout line endings only; API data and XLSX cells stay untouched.
module.exports = source => source.replace(/\r\n?/g, '\n');
