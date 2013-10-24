from collections import OrderedDict, MutableMapping
from operator import itemgetter


class Node(MutableMapping):
    """
    Recursive mapping to use as a `locals()` replacement in `eval`.
    """

    def __init__(self, *args, **kwargs):
        """Initialise the node."""

        self.data = OrderedDict()

        for arg in list(args) + [kwargs.items()]:
            for key, value in arg.items() if hasattr(arg, 'items') else arg:
                if (
                    isinstance(value, dict) or (
                        isinstance(value, (list, tuple)) and
                        all(
                            isinstance(v, tuple) and len(v) == 2
                            for v in value
                        )
                    )
                ):
                    self[key] = Node(value)
                else:
                    self[key] = value

    @staticmethod
    def _split_key(key):
        """Split up the key into head and tail."""

        # split up the key if it is a string
        if isinstance(key, (str, unicode)):
            if '.' in key:
                return itemgetter(0, 2)(key.partition('.'))
            else:
                return key, None

        try:
            return key[0], key[1:]
        except:
            return key, None

    def __getitem__(self, key):
        """Get an item from the node tree."""

        head, tail = Node._split_key(key)

        if tail:
            return self.data[head][tail]
        else:
            return self.data[head]

    def __getattr__(self, attr):
        """Get an item from the node tree."""

        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

    def __setitem__(self, key, value):
        """Set an item in the node tree."""

        head, tail = Node._split_key(key)

        # create a new node if one does not already exist or is not node
        if not head in self.data or not isinstance(self.data[head], Node):
            self.data[head] = Node()

        if tail:
            self.data[head][tail] = value
        else:
            self.data[head] = value

    def __delitem__(self, key):
        """Delete an item from the node tree."""

        head, tail = Node._split_key(key)

        if tail:
            del self.data[head][tail]
        else:
            del self.data[head]

    def __iter__(self):
        """Return an iterator over the keys in the node tree."""

        return (
            (key, ) + sub_key
            for key, value in self.data.items()
            for sub_key in (
                value if isinstance(value, Node) else ((), )
            )
        )

    def __len__(self):
        """Return the number of values in the node tree."""

        return sum(
            len(value) if isinstance(value, Node) else 1
            for key, value in self.data.items()
        )

    def __repr__(self):
        """String representation of the node tree."""

        items = ', '.join(
            "{0}: {1}".format(repr(key), repr(value))
            for key, value in self.items()
        )
        return 'Node({{0}})'.format(items)

    def __str__(self):
        """String representation of the node tree."""

        return repr(self)

    def to_dict(self):
        """Convert the node tree back to dictionaries."""

        return OrderedDict(
            (key, value.to_dict() if isinstance(value, Node) else value)
            for key, value in self.data.items()
        )

    def copy(self):
        """Shallow copy."""

        return Node(
            (key, value.copy() if isinstance(value, Node) else value)
            for key, value in self.data.items()
        )
