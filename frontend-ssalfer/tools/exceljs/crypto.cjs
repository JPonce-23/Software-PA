'use strict';
// ExcelJS encryptor only uses hashing and secure random bytes for worksheet
// protection. Do not bundle the unused sign/verify/ECDH crypto-browserify tree.
// randombytes fails closed when Web Crypto getRandomValues is unavailable.
exports.createHash = require('create-hash');
exports.randomBytes = require('randombytes');
exports.getHashes = () => ['sha1', 'sha224', 'sha256', 'sha384', 'sha512', 'md5', 'rmd160', 'ripemd160'];
