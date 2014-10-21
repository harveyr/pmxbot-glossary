# pmxbot-glossary

Glossary extension for [pmxbot](https://bitbucket.org/yougov/pmxbot/wiki/Home).

[![Build Status](https://travis-ci.org/harveyr/pmxbot-glossary.svg?branch=master)](https://travis-ci.org/harveyr/pmxbot-glossary)

## Commands

**Get a definition**

`!whatis carrot`

**Add a definition**

`!set carrot: An orange rod`

**Update a definition**

Same as adding one:

`!set carrot: An orange vegetable. For more, see http://en.wikipedia.org/wiki/Carrot`

This creates a new definition without overwriting the old one.

**Get an older definition**

`!whatis carrot: 1`

This returns the first definition. `!whatis carrot: 2` would return the second,
and so on.

**Get a random definition**

`!whatis`

**Redirect an entry to another**

`redirect burger: hamburger`

**Remove a redirect**

`unredirect burger`

 
## Why?

This extension is an effort to test the following hypothesis:

Maintaining definitions of domain lingo via a chat bot is the
best way to keep those definitions up to date and readily accessible
(assuming the group uses some form of internet chat).

This may be the case because:

* It allows painless updating of the definitions (no pull requests, etc.).
* It allows painless retrieval of the definitions.
* It provides a single entry point to docs that are spread among a number
  of sources (assuming you provide links).
* It enables somewhat automatic review of definitions as they are added
  or retrieved.
* It creates "accidental" education: you'll learn stuff just sitting in a
  channel and seeing the definitions scroll by.
* It keeps the definitions in front of the eyes of the
  domain experts, maximizing the chances they will spot an obsolete,
  misguided, or missing entry.
