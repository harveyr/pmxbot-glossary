# pmxbot-glossary changelog

**0.4.1**
*(Oct 22, 2014)*

* `!define` is back! Many thanks to Jason Coombs for providing the proper ways
to play with command-override priorities.
* `!set` is still there as well, as an alias.

**0.4.0**
*(Oct 21, 2014)*

* Removed `!define` and replaced it with `!set`. !define overrides a pmxbot
default, and the override stopped working for some unknown reason. Since there
is not a clear way to "properly" override a default command, we'll use something
new.
* Removed author from standard output. 
* Added !whowrote to get the author of an entry.

* README fixes.

**0.3.0**
*(Oct 20, 2014)*

* Added one-way redirects between entries. This adds a new table to the database.
* The commands are currently `redirect` and `unredirect`. 
* Added redirect data to json dump and load.

