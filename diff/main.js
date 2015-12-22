(function() {
  var DATA_URL = './data/';
  var emptyInterface = {
    'attributes': [],
    'constants': [],
    'operations': [],
  };

  function matchType(a, b) {
    return a.idl_type.base_type == b.idl_type.base_type;
  }

  function compareValues(a, b, typeSpecificCompare) {
    if (!a) return 1;
    if (!b) return -1;
    if (a.name != b.name)
      return a.name.localeCompare(b.name);
    if (!matchType(a, b))
      return -1;
    return typeSpecificCompare(a, b);
  }

  function Line(line, annotation) {
    this.line = line;
    this.annotation = annotation;
  }

  function sameLine(line) { return new Line(line, 'unchanged'); }
  function addedLine(line) { return new Line(line, 'added'); }
  function removedLine(line) { return new Line(line, 'removed'); }
  function emptyLine() { return new Line('', 'empty'); }

  function Model() {
    this._webkit_idls = null;
    this._blink_idls = null;
    this._interface_names = null;
  }

  Model.prototype = {
    get interfaceNames() {
      if (!this._interface_names) {
        var names = new Set();
        for (var name in this._webkit_idls) {
          names.add(name);
        }
        for (var name in this._blink_idls) {
          names.add(name);
        }
        this._interface_names = Array.from(names);
      }
      return this._interface_names;
    },
    getDiff: function(name) {
      var wk = this._webkit_idls[name] || emptyInterface;
      var bl = this._blink_idls[name] || emptyInterface;
      return {
        constants: this._diffConstants(wk, bl),
        attributes: this._diffAttributes(wk, bl),
        operations: this._diffOperations(wk, bl)
      };
    },
    _computeDiff: function(valuesA, valuesB, compare, toLine) {
      valuesA.sort((a, b) => compareValues(a, b, compare));
      valuesB.sort((a, b) => compareValues(a, b, compare));

      var linesA = [], linesB = [];
      var i = 0, j = 0;
      while (i < valuesA.length || j < valuesB.length) {
        var cmp = compareValues(valuesA[i], valuesB[j], compare);
        if (cmp == 0) {
          var line = toLine(valuesA[i]);
          linesA.push(sameLine(line));
          linesB.push(sameLine(line));
          i++;
          j++;
        } else if (cmp < 0) {
          linesA.push(removedLine(toLine(valuesA[i])));
          linesB.push(emptyLine());
          i++;
        } else {
          linesA.push(emptyLine());
          linesB.push(addedLine(toLine(valuesB[j])));
          j++;
        }
      }
      return {a: linesA, b: linesB};
    },
    _diffConstants: function(wk, bl) {
      return undefined;
    },
    _diffAttributes: function(wk, bl) {
      var compare = function(a, b) {
        for (var p of ['is_static', 'is_read_only']) {
          if (a[p] != b[p]) return -1;
        }
        return 0;
      };
      var toLine = function(attr) {
        return [
          attr.is_static ? 'static' : '',
          attr.is_read_only ? 'readonly' : '',
          attr.idl_type.base_type,
          attr.name + ';'
        ].join(' ').trim();
      };
      return this._computeDiff(
        wk['attributes'], bl['attributes'], compare, toLine);
    },
    _diffOperations: function(wk, bl) {
      var compareArgument = function(a, b) {
        for (var p of ['is_optional', 'is_variadic', 'default_value']) {
          if (a[p] != b[p])
            return -1;
        }
        return 0;
      };
      var compare = function(a, b) {
        if (a.is_static != b.is_static)
          return -1;
        if (a.arguments.length != b.arguments.length)
          return a.arguments.length - b.arguments.length;
        for (var i = 0; i < a.arguments.length; i++) {
          if (compareValues(a.arguments[i], b.arguments[i], compareArgument) != 0)
            return -1;
        }
        return 0;
      };
      var toLine = function(op) {
        var prefix = [op.is_static ? 'static' : '',
                      op.idl_type.base_type, op.name].join(' ').trim();
        var args = [];
        for (var arg of op.arguments) {
          var buf = [];
          if (arg.is_optional)
            buf.push('optional');
          buf.push(arg.idl_type.base_type);
          buf.push(arg.name);
          if (arg.default_value) {
            var value = arg.default_value.value;
            if (arg.default_value.idl_type == 'DOMString')
              value = '"' + value + '"';
            buf.push('= ' + value);
          }
          if (arg.is_variadic)
            buf.push('...');
          args.push(buf.join(' '));
        }
        return `${prefix}(${args.join(', ')});`;
      };
      return this._computeDiff(wk['operations'], bl['operations'],
                               compare, toLine);
    }
  };

  function createModel() {
    return new Promise(function(resolve, reject) {
      var model = new Model();
      $.ajax({
        url: DATA_URL + 'webkit.json',
      }).done(function(data) {
        model._webkit_idls = data;
        resolve(model);
      }).fail(function(error) {
        console.log(error);
      });
    }).then(function(model) {
      return new Promise(function(resolve, reject) {
        $.ajax({
          url: DATA_URL + 'blink.json',
        }).done(function(data) {
          model._blink_idls = data;
          resolve(model);
        }).fail(function(error) {
          console.log(error);
        });
      });
    });
  }

  function init() {
    createModel().then(function(m) {
      document.querySelector('#mainview').model = m;
    });
  }

  window.onload = init;
})();
