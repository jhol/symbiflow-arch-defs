#!/usr/bin/env python3
import enum
import io

from collections import namedtuple

from . import Pos
from . import Size
from . import static_property
from ..asserts import assert_type
from ..asserts import assert_len_eq


class ChannelNotStraight(TypeError):
    pass


_Channel = namedtuple("Channel", ("start", "end", "idx"))
class Channel(_Channel):
    class Type(enum.Enum):
        X = 'CHANX'
        Y = 'CHANY'

        def __repr__(self):
            return 'Channel.Type.'+self.name

    class Direction(enum.Enum):
        INC = 'INC_DIR'
        DEC = 'DEC_DIR'

        def __repr__(self):
            return 'Channel.Direction.'+self.name

    def __new__(cls, start, end, idx=None, id_override=None):
        if not isinstance(start, Pos):
            start = Pos(*start)
        if not isinstance(end, Pos):
            end = Pos(*end)

        if start.x != end.x and start.y != end.y:
            raise ChannelNotStraight(
                "Channel not straight! {}->{}".format(start, end))

        if idx is not None:
            assert_type(idx, int)

        obj = _Channel.__new__(cls, start, end, idx)
        obj.id_override = id_override
        return obj

    @static_property
    def type(self):
        """Type of the channel.

        Returns: Channel.Type

        >>> Channel((0, 0), (10, 0)).type
        Channel.Type.Y
        >>> Channel((0, 0), (0, 10)).type
        Channel.Type.X
        >>> Channel((1, 1), (1, 1)).type
        Channel.Type.X
        """
        if self.start.x == self.end.x:
            return Channel.Type.X
        elif self.start.y == self.end.y:
            return Channel.Type.Y
        else:
            assert False

    @static_property
    def start0(self):
        """The non-constant start coordinate.

        >>> Channel((0, 0), (10, 0)).start0
        0
        >>> Channel((0, 0), (0, 10)).start0
        0
        >>> Channel((1, 1), (1, 1)).start0
        1
        >>> Channel((10, 0), (0, 0)).start0
        10
        >>> Channel((0, 10), (0, 0)).start0
        10
        """
        if self.type == Channel.Type.Y:
            return self.start.x
        elif self.type == Channel.Type.X:
            return self.start.y
        else:
            assert False

    @static_property
    def end0(self):
        """The non-constant start coordinate.

        >>> Channel((0, 0), (10, 0)).end0
        10
        >>> Channel((0, 0), (0, 10)).end0
        0
        >>> Channel((1, 1), (1, 1)).end0
        1
        >>> Channel((10, 0), (0, 0)).end0
        0
        >>> Channel((0, 10), (0, 0)).end0
        0
        """
        if self.type == Channel.Type.Y:
            return self.end.x
        elif self.type == Channel.Type.X:
            return self.end.y
        else:
            assert False

    @static_property
    def common(self):
        """The common coordinate value.

        >>> Channel((0, 0), (10, 0)).common
        0
        >>> Channel((0, 0), (0, 10)).common
        0
        >>> Channel((1, 1), (1, 1)).common
        1
        >>> Channel((10, 0), (0, 0)).common
        0
        >>> Channel((0, 10), (0, 0)).common
        0
        >>> Channel((4, 10), (4, 0)).common
        4
        """
        if self.type == Channel.Type.Y:
            assert self.start.y == self.end.y
            return self.start.y
        elif self.type == Channel.Type.X:
            assert self.start.x == self.end.x
            return self.start.x
        else:
            assert False

    @static_property
    def direction(self):
        """Direction the channel runs.

        Returns: Channel.Direction

        >>> Channel((0, 0), (10, 0)).direction
        Channel.Direction.INC
        >>> Channel((0, 0), (0, 10)).direction
        Channel.Direction.INC
        >>> Channel((1, 1), (1, 1)).direction
        Channel.Direction.INC
        >>> Channel((10, 0), (0, 0)).direction
        Channel.Direction.DEC
        >>> Channel((0, 10), (0, 0)).direction
        Channel.Direction.DEC
        """
        if self.end0 < self.start0:
            return Channel.Direction.DEC
        else:
            return Channel.Direction.INC

    @static_property
    def length(self):
        """Length of the channel.

        >>> Channel((0, 0), (10, 0)).length
        10
        >>> Channel((0, 0), (0, 10)).length
        10
        >>> Channel((1, 1), (1, 1)).length
        0
        >>> Channel((10, 0), (0, 0)).length
        10
        >>> Channel((0, 10), (0, 0)).length
        10
        """
        return abs(self.end0 - self.start0)

    def update_idx(self, idx):
        """Create a new channel with the same start/end but new index value.

        >>> s = (1, 4)
        >>> e = (1, 8)
        >>> c1 = Channel(s, e, 0)
        >>> c2 = c1.update_idx(2)
        >>> assert c1.start == c2.start
        >>> assert c1.end == c2.end
        >>> c1.idx
        0
        >>> c2.idx
        2
        """
        return self.__class__(self.start, self.end, idx, id_override=self.id_override)

    def __repr__(self):
        """

        >>> repr(Channel((0, 0), (10, 0)))
        'C((0,0), (10,0))'
        >>> repr(Channel((0, 0), (0, 10)))
        'C((0,0), (0,10))'
        >>> repr(Channel((1, 2), (3, 2), 5))
        'C((1,2), (3,2), 5)'
        >>> repr(Channel((1, 2), (3, 2), None, "ABC"))
        'C(ABC)'
        >>> repr(Channel((1, 2), (3, 2), 5, "ABC"))
        'C(ABC,5)'
        """
        if self.id_override:
            idx_str = ""
            if self.idx != None:
                idx_str = ",{}".format(self.idx)
            return "C({}{})".format(self.id_override, idx_str)

        idx_str = ""
        if self.idx != None:
            idx_str = ", {}".format(self.idx)
        return "C(({},{}), ({},{}){})".format(
            self.start.x, self.start.y, self.end.x, self.end.y, idx_str)

    def __str__(self):
        """

        >>> str(Channel((0, 0), (10, 0)))
        'CHANY 0,0->10,0'
        >>> str(Channel((0, 0), (0, 10)))
        'CHANX 0,0->0,10'
        >>> str(Channel((1, 2), (3, 2), 5))
        'CHANY 1,2->3,2 @5'
        >>> str(Channel((1, 2), (3, 2), None, "ABC"))
        'ABC'
        >>> str(Channel((1, 2), (3, 2), 5, "ABC"))
        'ABC@5'
        """
        idx_str = ""
        if self.idx != None:
            idx_str = " @{}".format(self.idx)
        if self.id_override:
            return "{}{}".format(self.id_override, idx_str[1:])
        return "{} {},{}->{},{}{}".format(
            self.type.value, self.start.x, self.start.y, self.end.x, self.end.y, idx_str)


# Nice short alias..
C = Channel


class ChannelGrid(dict):
    def __init__(self, size, chan_type):
        self.chan_type = chan_type
        self.size = Size(*size)

        for x in range(0, self.x):
            for y in range(0, self.y):
                self[Pos(x,y)] = []

    @property
    def x(self):
        return self.size.x

    @property
    def y(self):
        return self.size.y

    def column(self, x):
        column = []
        for y in range(0, self.y):
            column.append(self[Pos(x, y)])
        return column

    def row(self, y):
        row = []
        for x in range(0, self.x):
            row.append(self[Pos(x, y)])
        return row

    def add_channel(self, ch):
        """
        >>> g = ChannelGrid((10, 10), Channel.Type.Y)
        >>> # Adding the first channel
        >>> g.add_channel(Channel((0, 5), (3, 5), None, "A"))
        C(A,0)
        >>> g[(0,5)]
        [C(A,0)]
        >>> g[(1,5)]
        [C(A,0)]
        >>> g[(3,5)]
        [C(A,0)]
        >>> g[(4,5)]
        [None]
        >>> # Adding second non-overlapping second channel
        >>> g.add_channel(Channel((4, 5), (6, 5), None, "B"))
        C(B,0)
        >>> g[(3,5)]
        [C(A,0)]
        >>> g[(4,5)]
        [C(B,0)]
        >>> g[(6,5)]
        [C(B,0)]
        >>> g[(7,5)]
        [None]
        >>> # Adding third channel which overlaps with second channel
        >>> g.add_channel(Channel((4, 5), (6, 5), None, "C"))
        C(C,1)
        >>> g[(3,5)]
        [C(A,0), None]
        >>> g[(4,5)]
        [C(B,0), C(C,1)]
        >>> g[(6,5)]
        [C(B,0), C(C,1)]
        >>> # Adding a channel which overlaps, but is a row over
        >>> g.add_channel(Channel((4, 6), (6, 6), None, "D"))
        C(D,0)
        >>> g[(4,5)]
        [C(B,0), C(C,1)]
        >>> g[(4,6)]
        [C(D,0)]
        >>> # Adding fourth channel which overlaps both the first
        >>> # and second+third channel
        >>> g.add_channel(Channel((2, 5), (5, 5), None, "E"))
        C(E,2)
        >>> g[(1,5)]
        [C(A,0), None, None]
        >>> g[(2,5)]
        [C(A,0), None, C(E,2)]
        >>> g[(5,5)]
        [C(B,0), C(C,1), C(E,2)]
        >>> g[(6,5)]
        [C(B,0), C(C,1), None]
        >>> # This channel fits in the hole left by the last one.
        >>> g.add_channel(Channel((0, 5), (2, 5), None, "F"))
        C(F,1)
        >>> g[(0,5)]
        [C(A,0), C(F,1), None]
        >>> g[(1,5)]
        [C(A,0), C(F,1), None]
        >>> g[(2,5)]
        [C(A,0), C(F,1), C(E,2)]
        >>> g[(3,5)]
        [C(A,0), None, C(E,2)]
        >>> # Add another channel which causes a hole
        >>> g.add_channel(Channel((0, 5), (6, 5), None, "G"))
        C(G,3)
        >>> g[(0,5)]
        [C(A,0), C(F,1), None, C(G,3)]
        >>> g[(1,5)]
        [C(A,0), C(F,1), None, C(G,3)]
        >>> g[(2,5)]
        [C(A,0), C(F,1), C(E,2), C(G,3)]
        >>> g[(3,5)]
        [C(A,0), None, C(E,2), C(G,3)]
        >>> g[(4,5)]
        [C(B,0), C(C,1), C(E,2), C(G,3)]
        >>> g[(5,5)]
        [C(B,0), C(C,1), C(E,2), C(G,3)]
        >>> g[(6,5)]
        [C(B,0), C(C,1), None, C(G,3)]
        >>> g[(7,5)]
        [None, None, None, None]
        """
        assert ch.idx == None

        if ch.type != self.chan_type:
            if ch.length != 0:
                raise TypeError(
                    "Can only add channels of type {} which {} ({}) is not.".format(
                        self.chan_type, ch, ch.type))
            else:
                ch.type = self.chan_type

        if ch.type == Channel.Type.X:
            l = self.column(ch.common)
        elif ch.type == Channel.Type.Y:
            l = self.row(ch.common)
        else:
            assert False

        assert_len_eq(l)

        s = ch.start0
        e = ch.end0
        if ch.direction == Channel.Direction.DEC:
            e, s = s, e

        assert e >= s

        assert s < len(l), (s, '<', len(l), l)
        assert e < len(l), (e+1, '<', len(l), l)

        # Find a idx that this channel fits.
        max_idx = 0
        while True:
            for p in l[s:e+1]:
                while len(p) < max_idx+1:
                    p.append(None)
                if p[max_idx] != None:
                    max_idx += 1
                    break
            else:
                break

        # Make sure everything has the same length.
        for p in l:
            while len(p) < max_idx+1:
                p.append(None)

        assert_len_eq(l)

        ch = ch.update_idx(max_idx)
        assert ch.idx == max_idx
        for p in l[s:e+1]:
            p[ch.idx] = ch
        return ch

    def pretty_print(self):
        """
        If type == Channel.Type.X

          A--AC-C
          B-----B

          D--DE-E
          F-----F

        If type == Channel.Type.Y

          AB  DF
          ||  ||
          ||  ||
          A|  D|
          C|  E|
          ||  ||
          CB  EF

        """

        def get_str(ch):
            if not ch:
                s = ""
            elif ch.id_override:
                s = ch.id_override
            else:
                s = str(ch)
            return s

        # Work out how many characters the largest label takes up.
        s_maxlen = 1
        for row in range(0, self.y):
            for col in range(0, self.x):
                for ch in self[(col,row)]:
                    s_maxlen = max(s_maxlen, len(get_str(ch)))

        assert s_maxlen > 0, s_maxlen
        s_maxlen += 3
        if self.chan_type == Channel.Type.Y:
            beg_fmt  = "{:>%i}>" % (s_maxlen-1)
            end_fmt = "->{:<%i}" % (s_maxlen-2)
            mid_fmt = "-"*s_maxlen
        elif self.chan_type == Channel.Type.X:
            beg_fmt = "{:^%i}" % s_maxlen
            end_fmt = beg_fmt
            mid_fmt = beg_fmt.format("|")
        else:
            assert False
        non_fmt = " "*s_maxlen

        rows = []
        for y in range(0, self.y):
            cols = []
            for x in range(0, self.x):
                channels = [("|{: ^%i}" % (s_maxlen-1)).format(x)]
                for ch in self[(x,y)]:
                    if not ch:
                        fmt = non_fmt
                    elif ch.start == ch.end:
                        s = get_str(ch)
                        channels.append("{} ".format("".join([
                                beg_fmt.format(s),
                                mid_fmt.format(s),
                                end_fmt.format(s),
                            ])[:s_maxlen-1]))
                        continue
                    elif ch.start == (x,y):
                        fmt = beg_fmt
                    elif ch.end == (x,y):
                        fmt = end_fmt
                    else:
                        fmt = mid_fmt

                    channels.append(fmt.format(get_str(ch)))
                cols.append(channels)
            rows.append(cols)


        f = io.StringIO()
        def p(*args, **kw):
            print(*args, file=f, **kw)
        for r in range(0, len(rows)):
            assert_len_eq(rows[r])
            for i in range(0, len(rows[r][0])):
                for c in range(0, len(rows[r])):
                    p(rows[r][c][i], end="")
                if i == 0:
                    p("|", end="")
                p()
            p("\n")
        return f.getvalue()


class Channels:
    def __init__(self, size):
        self.size = size
        self.x = ChannelGrid(size, Channels.Type.X)
        self.y = ChannelGrid(size, Channels.Type.Y)

    def create_channel(self, start, end):
        if ch.type != self.chan_type:
            raise TypeError(
                "Can only add channels of type {} which {} ({}) is not.".format(
                    self.chan_type, ch, ch.type))
        try:
            ch = Channel(start, end)
        except ChannelNotStraight as e:
            corner = (start.x, end.y)
            ch_a = self.create_channel(start, corner)[0]
            ch_b = self.create_channel(corner, end)[0]
            return (ch_a, ch_b)

        if ch.type == Channel.Type.X:
            self.x.add_channel(ch)
        elif ch.type == Channel.Type.Y:
            self.y.add_channel(ch)
        else:
            assert False

        if ch.type == Channel.Type.X:
            l = self.column(ch.common)
        elif ch.type == Channel.Type.Y:
            l = self.row(ch.common)
        else:
            assert False


if __name__ == "__main__":
    import doctest
    doctest.testmod()

    g = ChannelGrid((5,2), Channel.Type.Y)
    g.add_channel(C((0,0), (4,0), None, "AA"))
    g.add_channel(C((0,0), (2,0), None, "BB"))
    g.add_channel(C((1,0), (4,0), None, "CC"))
    g.add_channel(C((0,0), (0,0), None, "DD"))

    g.add_channel(C((0,1), (2,1), None, "aa"))
    g.add_channel(C((3,1), (4,1), None, "bb"))
    g.add_channel(C((0,1), (4,1), None, "cc"))

    print()
    print(g.pretty_print())
