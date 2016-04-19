import abc
import contextlib
import collections
import pickle
import re
import sys
from unittest import TestCase, main, skipUnless

from typing import Any
from typing import TypeVar, AnyStr
from typing import T, KT, VT  # Not in __all__.
from typing import Union, Optional
from typing import Tuple
from typing import Callable
from typing import Generic
from typing import cast
from typing import get_type_hints
from typing import is_compatible
from typing import no_type_check, no_type_check_decorator
from typing import NamedTuple
from typing import IO, TextIO, BinaryIO
from typing import Pattern, Match
import typing


class Employee:
    pass


class Manager(Employee):
    pass


class Founder(Employee):
    pass


class ManagingFounder(Manager, Founder):
    pass


class AnyTests(TestCase):

    def test_any_type_errors(self):
        with self.assertRaises(TypeError):
            isinstance(42, Any)
        with self.assertRaises(TypeError):
            issubclass(Employee, Any)

    def test_compatible_with_classes(self):
        self.assertTrue(is_compatible(Employee, Any))
        self.assertTrue(is_compatible(int, Any))
        self.assertTrue(is_compatible(type(None), Any))
        self.assertTrue(is_compatible(object, Any))
        self.assertTrue(is_compatible(Any, Employee))
        self.assertTrue(is_compatible(Any, int))
        self.assertTrue(is_compatible(Any, type(None)))
        self.assertTrue(is_compatible(Any, object))

    def test_not_a_subclass(self):
        self.assertFalse(issubclass(Any, Employee))
        self.assertFalse(issubclass(Any, int))
        self.assertFalse(issubclass(Any, type(None)))
        self.assertFalse(issubclass(Any, typing.Generic))
        self.assertFalse(issubclass(Any, typing.Iterable))
        # However, Any is a subclass of object (this can't be helped).
        self.assertTrue(issubclass(Any, object))

    def test_repr(self):
        self.assertEqual(repr(Any), 'typing.Any')

    def test_errors(self):
        with self.assertRaises(TypeError):
            issubclass(42, Any)
        with self.assertRaises(TypeError):
            Any[int]  # Any is not a generic type.

    def test_cannot_subclass(self):
        with self.assertRaises(TypeError):
            class A(Any):
                pass

    def test_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            Any()

    def test_cannot_subscript(self):
        with self.assertRaises(TypeError):
            Any[int]

    def test_compatible_with_types(self):
        # Any should be considered compatible with everything.
        assert is_compatible(Any, Any)
        assert is_compatible(Any, typing.List)
        assert is_compatible(Any, typing.List[int])
        assert is_compatible(Any, typing.List[T])
        assert is_compatible(Any, typing.Mapping)
        assert is_compatible(Any, typing.Mapping[str, int])
        assert is_compatible(Any, typing.Mapping[KT, VT])
        assert is_compatible(Any, Generic)
        assert is_compatible(Any, Generic[T])
        assert is_compatible(Any, Generic[KT, VT])
        assert is_compatible(Any, AnyStr)
        assert is_compatible(Any, Union)
        assert is_compatible(Any, Union[int, str])
        assert is_compatible(Any, typing.Match)
        assert is_compatible(Any, typing.Match[str])
        assert is_compatible(Generic, Any)
        assert is_compatible(Union, Any)
        assert is_compatible(Match, Any)
        # These expressions must simply not fail.
        typing.Match[Any]
        typing.Pattern[Any]
        typing.IO[Any]


class TypeVarTests(TestCase):

    def test_basic_plain(self):
        T = TypeVar('T')
        # Every class is a subtype of T.
        assert is_compatible(int, T)
        assert is_compatible(str, T)
        # T equals itself.
        assert T == T
        # T is a subtype of itself.
        assert is_compatible(T, T)
        # T is an instance of TypeVar
        assert isinstance(T, TypeVar)

    def test_typevar_type_errors(self):
        T = TypeVar('T')
        with self.assertRaises(TypeError):
            isinstance(42, T)
        with self.assertRaises(TypeError):
            issubclass(int, T)

    def test_basic_constrained(self):
        A = TypeVar('A', str, bytes)
        # Only str and bytes are subtypes of A.
        assert is_compatible(str, A)
        assert is_compatible(bytes, A)
        assert not is_compatible(int, A)
        # A equals itself.
        assert A == A
        # A is a subtype of itself.
        assert is_compatible(A, A)

    def test_constrained_error(self):
        with self.assertRaises(TypeError):
            X = TypeVar('X', int)
            X

    def test_union_unique(self):
        X = TypeVar('X')
        Y = TypeVar('Y')
        assert X != Y
        assert Union[X] == X
        assert Union[X] != Union[X, Y]
        assert Union[X, X] == X
        assert Union[X, int] != Union[X]
        assert Union[X, int] != Union[int]
        assert Union[X, int].__union_params__ == (X, int)
        assert Union[X, int].__union_set_params__ == {X, int}

    def test_union_constrained(self):
        A = TypeVar('A', str, bytes)
        assert Union[A, str] != Union[A]

    def test_repr(self):
        self.assertEqual(repr(T), '~T')
        self.assertEqual(repr(KT), '~KT')
        self.assertEqual(repr(VT), '~VT')
        self.assertEqual(repr(AnyStr), '~AnyStr')
        T_co = TypeVar('T_co', covariant=True)
        self.assertEqual(repr(T_co), '+T_co')
        T_contra = TypeVar('T_contra', contravariant=True)
        self.assertEqual(repr(T_contra), '-T_contra')

    def test_no_redefinition(self):
        self.assertNotEqual(TypeVar('T'), TypeVar('T'))
        self.assertNotEqual(TypeVar('T', int, str), TypeVar('T', int, str))

    def test_subclass_as_unions(self):
        # None of these are true -- each type var is its own world.
        self.assertFalse(is_compatible(TypeVar('T', int, str),
                                       TypeVar('T', int, str)))
        self.assertFalse(is_compatible(TypeVar('T', int, float),
                                       TypeVar('T', int, float, str)))
        self.assertFalse(is_compatible(TypeVar('T', int, str),
                                       TypeVar('T', str, int)))
        A = TypeVar('A', int, str)
        B = TypeVar('B', int, str, float)
        self.assertFalse(is_compatible(A, B))
        self.assertFalse(is_compatible(B, A))

    def test_cannot_subclass_vars(self):
        with self.assertRaises(TypeError):
            class V(TypeVar('T')):
                pass

    def test_cannot_subclass_var_itself(self):
        with self.assertRaises(TypeError):
            class V(TypeVar):
                pass

    def test_cannot_instantiate_vars(self):
        with self.assertRaises(TypeError):
            TypeVar('A')()

    def test_bound(self):
        X = TypeVar('X', bound=Employee)
        assert is_compatible(Employee, X)
        assert is_compatible(Manager, X)
        assert not is_compatible(int, X)

    def test_bound_errors(self):
        with self.assertRaises(TypeError):
            TypeVar('X', bound=42)
        with self.assertRaises(TypeError):
            TypeVar('X', str, float, bound=Employee)


class UnionTests(TestCase):

    def test_basics(self):
        u = Union[int, float]
        self.assertNotEqual(u, Union)
        self.assertTrue(is_compatible(int, u))
        self.assertTrue(is_compatible(float, u))

    def test_union_any(self):
        u = Union[Any]
        self.assertEqual(u, Any)
        u = Union[int, Any]
        self.assertEqual(u, Any)
        u = Union[Any, int]
        self.assertEqual(u, Any)

    def test_union_object(self):
        u = Union[object]
        self.assertEqual(u, object)
        u = Union[int, object]
        self.assertEqual(u, object)
        u = Union[object, int]
        self.assertEqual(u, object)

    def test_union_any_object(self):
        u = Union[object, Any]
        self.assertEqual(u, Any)
        u = Union[Any, object]
        self.assertEqual(u, Any)

    def test_unordered(self):
        u1 = Union[int, float]
        u2 = Union[float, int]
        self.assertEqual(u1, u2)

    def test_subclass(self):
        u = Union[int, Employee]
        self.assertTrue(is_compatible(Manager, u))

    def test_self_subclass(self):
        self.assertTrue(is_compatible(Union[KT, VT], Union))
        self.assertFalse(is_compatible(Union, Union[KT, VT]))

    def test_multiple_inheritance(self):
        u = Union[int, Employee]
        self.assertTrue(is_compatible(ManagingFounder, u))

    def test_single_class_disappears(self):
        t = Union[Employee]
        self.assertIs(t, Employee)

    def test_base_class_disappears(self):
        u = Union[Employee, Manager, int]
        self.assertEqual(u, Union[int, Employee])
        u = Union[Manager, int, Employee]
        self.assertEqual(u, Union[int, Employee])
        u = Union[Employee, Manager]
        self.assertIs(u, Employee)

    def test_weird_subclasses(self):
        u = Union[Employee, int, float]
        v = Union[int, float]
        self.assertTrue(is_compatible(v, u))
        w = Union[int, Manager]
        self.assertTrue(is_compatible(w, u))

    def test_union_union(self):
        u = Union[int, float]
        v = Union[u, Employee]
        self.assertEqual(v, Union[int, float, Employee])

    def test_repr(self):
        self.assertEqual(repr(Union), 'typing.Union')
        u = Union[Employee, int]
        self.assertEqual(repr(u), 'typing.Union[%s.Employee, int]' % __name__)
        u = Union[int, Employee]
        self.assertEqual(repr(u), 'typing.Union[int, %s.Employee]' % __name__)

    def test_cannot_subclass(self):
        with self.assertRaises(TypeError):
            class C(Union):
                pass
        with self.assertRaises(TypeError):
            class C(Union[int, str]):
                pass

    def test_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            Union()
        u = Union[int, float]
        with self.assertRaises(TypeError):
            u()

    def test_optional(self):
        o = Optional[int]
        u = Union[int, None]
        self.assertEqual(o, u)

    def test_empty(self):
        with self.assertRaises(TypeError):
            Union[()]

    def test_is_compatible(self):
        assert is_compatible(Union[int, str], Union)
        assert not is_compatible(int, Union)

    def test_union_type_errors(self):
        with self.assertRaises(TypeError):
            isinstance(42, Union[int, str])
        with self.assertRaises(TypeError):
            issubclass(int, Union[int, str])

    def test_union_str_pattern(self):
        # Shouldn't crash; see http://bugs.python.org/issue25390
        A = Union[str, Pattern]
        A


class TypeVarUnionTests(TestCase):

    def test_simpler(self):
        A = TypeVar('A', int, str, float)
        B = TypeVar('B', int, str)
        assert is_compatible(A, A)
        assert is_compatible(B, B)
        assert not is_compatible(B, A)
        assert is_compatible(A, Union[int, str, float])
        assert not is_compatible(Union[int, str, float], A)
        assert not is_compatible(Union[int, str], B)
        assert is_compatible(B, Union[int, str])
        assert not is_compatible(A, B)
        assert not is_compatible(Union[int, str, float], B)
        assert not is_compatible(A, Union[int, str])

    def test_var_union_subtype(self):
        self.assertTrue(is_compatible(T, Union[int, T]))
        self.assertTrue(is_compatible(KT, Union[KT, VT]))

    def test_var_union(self):
        TU = TypeVar('TU', Union[int, float], None)
        assert is_compatible(int, TU)
        assert is_compatible(float, TU)


class TupleTests(TestCase):

    def test_basics(self):
        self.assertTrue(is_compatible(Tuple[int, str], Tuple))
        self.assertTrue(is_compatible(Tuple[int, str], Tuple[int, str]))
        self.assertFalse(is_compatible(int, Tuple))
        self.assertFalse(is_compatible(Tuple[float, str], Tuple[int, str]))
        self.assertFalse(is_compatible(Tuple[int, str, int], Tuple[int, str]))
        self.assertFalse(is_compatible(Tuple[int, str], Tuple[int, str, int]))
        self.assertTrue(is_compatible(tuple, Tuple))
        self.assertFalse(is_compatible(Tuple, tuple))  # Can't have it both ways.

    def test_equality(self):
        assert Tuple[int] == Tuple[int]
        assert Tuple[int, ...] == Tuple[int, ...]
        assert Tuple[int] != Tuple[int, int]
        assert Tuple[int] != Tuple[int, ...]

    def test_tuple_subclass(self):
        class MyTuple(tuple):
            pass
        self.assertTrue(is_compatible(MyTuple, Tuple))

    def test_tuple_type_errors(self):
        with self.assertRaises(TypeError):
            isinstance((0, 0), Tuple[int, int])
        with self.assertRaises(TypeError):
            isinstance((0, 0), Tuple)
        with self.assertRaises(TypeError):
            issubclass(tuple, Tuple)

    def test_tuple_ellipsis_subclass(self):

        class B:
            pass

        class C(B):
            pass

        assert not is_compatible(Tuple[B], Tuple[B, ...])
        assert is_compatible(Tuple[C, ...], Tuple[B, ...])
        assert not is_compatible(Tuple[C, ...], Tuple[B])
        assert not is_compatible(Tuple[C], Tuple[B, ...])

    def test_repr(self):
        self.assertEqual(repr(Tuple), 'typing.Tuple')
        self.assertEqual(repr(Tuple[()]), 'typing.Tuple[]')
        self.assertEqual(repr(Tuple[int, float]), 'typing.Tuple[int, float]')
        self.assertEqual(repr(Tuple[int, ...]), 'typing.Tuple[int, ...]')


class CallableTests(TestCase):

    def test_self_subclass(self):
        self.assertTrue(is_compatible(Callable[[int], int], Callable))
        self.assertFalse(is_compatible(Callable, Callable[[int], int]))
        self.assertTrue(is_compatible(Callable[[int], int], Callable[[int], int]))
        self.assertFalse(is_compatible(Callable[[Employee], int],
                                       Callable[[Manager], int]))
        self.assertFalse(is_compatible(Callable[[Manager], int],
                                       Callable[[Employee], int]))
        self.assertFalse(is_compatible(Callable[[int], Employee],
                                       Callable[[int], Manager]))
        self.assertFalse(is_compatible(Callable[[int], Manager],
                                       Callable[[int], Employee]))

    def test_eq_hash(self):
        self.assertEqual(Callable[[int], int], Callable[[int], int])
        self.assertEqual(len({Callable[[int], int], Callable[[int], int]}), 1)
        self.assertNotEqual(Callable[[int], int], Callable[[int], str])
        self.assertNotEqual(Callable[[int], int], Callable[[str], int])
        self.assertNotEqual(Callable[[int], int], Callable[[int, int], int])
        self.assertNotEqual(Callable[[int], int], Callable[[], int])
        self.assertNotEqual(Callable[[int], int], Callable)

    def test_cannot_subclass(self):
        with self.assertRaises(TypeError):

            class C(Callable):
                pass

        with self.assertRaises(TypeError):

            class C(Callable[[int], int]):
                pass

    def test_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            Callable()
        c = Callable[[int], str]
        with self.assertRaises(TypeError):
            c()

    def test_callable_isinstance_works(self):
        def f():
            pass
        assert isinstance(f, Callable)
        assert not isinstance(None, Callable)

    def test_callable_issubclass_works(self):
        def f():
            pass
        assert issubclass(type(f), Callable)
        assert not issubclass(type(None), Callable)

    def test_callable_type_errora(self):
        def f():
            pass
        with self.assertRaises(TypeError):
            isinstance(f, Callable[[], None])
        with self.assertRaises(TypeError):
            isinstance(f, Callable[[], Any])
        with self.assertRaises(TypeError):
            isinstance(None, Callable[[], None])
        with self.assertRaises(TypeError):
            isinstance(None, Callable[[], Any])
        with self.assertRaises(TypeError):
            issubclass(type(f), Callable[[], None])
        with self.assertRaises(TypeError):
            issubclass(type(f), Callable[[], Any])

    def test_repr(self):
        ct0 = Callable[[], bool]
        self.assertEqual(repr(ct0), 'typing.Callable[[], bool]')
        ct2 = Callable[[str, float], int]
        self.assertEqual(repr(ct2), 'typing.Callable[[str, float], int]')
        ctv = Callable[..., str]
        self.assertEqual(repr(ctv), 'typing.Callable[..., str]')

    def test_callable_with_ellipsis(self):

        def foo(a: Callable[..., T]):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': Callable[..., T]})


XK = TypeVar('XK', str, bytes)
XV = TypeVar('XV')


class SimpleMapping(Generic[XK, XV]):

    def __getitem__(self, key: XK) -> XV:
        ...

    def __setitem__(self, key: XK, value: XV):
        ...

    def get(self, key: XK, default: XV = None) -> XV:
        ...


class MySimpleMapping(SimpleMapping[XK, XV]):

    def __init__(self):
        self.store = {}

    def __getitem__(self, key: str):
        return self.store[key]

    def __setitem__(self, key: str, value):
        self.store[key] = value

    def get(self, key: str, default=None):
        try:
            return self.store[key]
        except KeyError:
            return default


class ProtocolTests(TestCase):

    def test_supports_int(self):
        assert is_compatible(int, typing.SupportsInt)
        assert not issubclass(int, typing.SupportsInt)
        assert not is_compatible(str, typing.SupportsInt)

    def test_supports_float(self):
        assert is_compatible(float, typing.SupportsFloat)
        assert not is_compatible(str, typing.SupportsFloat)

    def test_supports_complex(self):

        # Note: complex itself doesn't have __complex__.
        class C:
            def __complex__(self):
                return 0j

        assert is_compatible(C, typing.SupportsComplex)
        assert not is_compatible(str, typing.SupportsComplex)

    def test_supports_bytes(self):

        # Note: bytes itself doesn't have __bytes__.
        class B:
            def __bytes__(self):
                return b''

        assert is_compatible(B, typing.SupportsBytes)
        assert not is_compatible(str, typing.SupportsBytes)

    def test_supports_abs(self):
        assert is_compatible(float, typing.SupportsAbs)
        assert is_compatible(int, typing.SupportsAbs)
        assert not is_compatible(str, typing.SupportsAbs)

    def test_supports_round(self):
        is_compatible(float, typing.SupportsRound)
        assert is_compatible(float, typing.SupportsRound)
        assert is_compatible(int, typing.SupportsRound)
        assert not is_compatible(str, typing.SupportsRound)

    def test_reversible(self):
        assert is_compatible(list, typing.Reversible)
        assert not is_compatible(int, typing.Reversible)

    def test_protocol_instance_type_error(self):
        with self.assertRaises(TypeError):
            isinstance(0, typing.SupportsAbs)


class GenericTests(TestCase):

    def test_basics(self):
        X = SimpleMapping[str, Any]
        assert X.__parameters__ == ()
        with self.assertRaises(TypeError):
            X[str]
        with self.assertRaises(TypeError):
            X[str, str]
        Y = SimpleMapping[XK, str]
        assert Y.__parameters__ == (XK,)
        Y[str]
        with self.assertRaises(TypeError):
            Y[str, str]

    def test_init(self):
        T = TypeVar('T')
        S = TypeVar('S')
        with self.assertRaises(TypeError):
            Generic[T, T]
        with self.assertRaises(TypeError):
            Generic[T, S, T]

    def test_repr(self):
        self.assertEqual(repr(SimpleMapping),
                         __name__ + '.' + 'SimpleMapping<~XK, ~XV>')
        self.assertEqual(repr(MySimpleMapping),
                         __name__ + '.' + 'MySimpleMapping<~XK, ~XV>')

    def test_chain_repr(self):
        T = TypeVar('T')
        S = TypeVar('S')

        class C(Generic[T]):
            pass

        X = C[Tuple[S, T]]
        assert X == C[Tuple[S, T]]
        assert X != C[Tuple[T, S]]

        Y = X[T, int]
        assert Y == X[T, int]
        assert Y != X[S, int]
        assert Y != X[T, str]

        Z = Y[str]
        assert Z == Y[str]
        assert Z != Y[int]
        assert Z != Y[T]

        assert str(Z).endswith(
            '.C<~T>[typing.Tuple[~S, ~T]]<~S, ~T>[~T, int]<~T>[str]')

    def test_dict(self):
        T = TypeVar('T')

        class B(Generic[T]):
            pass

        b = B()
        b.foo = 42
        self.assertEqual(b.__dict__, {'foo': 42})

        class C(B[int]):
            pass

        c = C()
        c.bar = 'abc'
        self.assertEqual(c.__dict__, {'bar': 'abc'})

    def test_pickle(self):
        global C  # pickle wants to reference the class by name
        T = TypeVar('T')

        class B(Generic[T]):
            pass

        class C(B[int]):
            pass

        c = C()
        c.foo = 42
        c.bar = 'abc'
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            z = pickle.dumps(c, proto)
            x = pickle.loads(z)
            self.assertEqual(x.foo, 42)
            self.assertEqual(x.bar, 'abc')
            self.assertEqual(x.__dict__, {'foo': 42, 'bar': 'abc'})

    def test_errors(self):
        with self.assertRaises(TypeError):
            B = SimpleMapping[XK, Any]

            class C(Generic[B]):
                pass

    def test_repr_2(self):
        PY32 = sys.version_info[:2] < (3, 3)

        class C(Generic[T]):
            pass

        assert C.__module__ == __name__
        if not PY32:
            assert C.__qualname__ == 'GenericTests.test_repr_2.<locals>.C'
        assert repr(C).split('.')[-1] == 'C<~T>'
        X = C[int]
        assert X.__module__ == __name__
        if not PY32:
            assert X.__qualname__ == 'C'
        assert repr(X).split('.')[-1] == 'C<~T>[int]'

        class Y(C[int]):
            pass

        assert Y.__module__ == __name__
        if not PY32:
            assert Y.__qualname__ == 'GenericTests.test_repr_2.<locals>.Y'
        assert repr(Y).split('.')[-1] == 'Y'

    def test_eq_1(self):
        assert Generic == Generic
        assert Generic[T] == Generic[T]
        assert Generic[KT] != Generic[VT]

    def test_eq_2(self):

        class A(Generic[T]):
            pass

        class B(Generic[T]):
            pass

        assert A == A
        assert A != B
        assert A[T] == A[T]
        assert A[T] != B[T]

    def test_multiple_inheritance(self):

        class A(Generic[T, VT]):
            pass

        class B(Generic[KT, T]):
            pass

        class C(A[T, VT], Generic[VT, T, KT], B[KT, T]):
            pass

        assert C.__parameters__ == (VT, T, KT)

    def test_nested(self):

        G = Generic

        class Visitor(G[T]):

            a = None

            def set(self, a: T):
                self.a = a

            def get(self):
                return self.a

            def visit(self) -> T:
                return self.a

        V = Visitor[typing.List[int]]

        class IntListVisitor(V):

            def append(self, x: int):
                self.a.append(x)

        a = IntListVisitor()
        a.set([])
        a.append(1)
        a.append(42)
        assert a.get() == [1, 42]

    def test_type_erasure(self):
        T = TypeVar('T')

        class Node(Generic[T]):
            def __init__(self, label: T,
                         left: 'Node[T]' = None,
                         right: 'Node[T]' = None):
                self.label = label  # type: T
                self.left = left  # type: Optional[Node[T]]
                self.right = right  # type: Optional[Node[T]]

        def foo(x: T):
            a = Node(x)
            b = Node[T](x)
            c = Node[Any](x)
            assert type(a) is Node
            assert type(b) is Node
            assert type(c) is Node
            assert a.label == x
            assert b.label == x
            assert c.label == x

        foo(42)

    def test_implicit_any(self):
        T = TypeVar('T')

        class C(Generic[T]):
            pass

        class D(C):
            pass

        assert D.__parameters__ == ()

        with self.assertRaises(Exception):
            D[int]
        with self.assertRaises(Exception):
            D[Any]
        with self.assertRaises(Exception):
            D[T]


class VarianceTests(TestCase):

    def test_invariance(self):
        # Because of invariance, List[subclass of X] is not a subclass
        # of List[X], and ditto for MutableSequence.
        assert not is_compatible(typing.List[Manager], typing.List[Employee])
        assert not is_compatible(typing.MutableSequence[Manager],
                                 typing.MutableSequence[Employee])
        # It's still reflexive.
        assert is_compatible(typing.List[Employee], typing.List[Employee])
        assert is_compatible(typing.MutableSequence[Employee],
                             typing.MutableSequence[Employee])

    def test_covariance_tuple(self):
        # Check covariace for Tuple (which are really special cases).
        assert is_compatible(Tuple[Manager], Tuple[Employee])
        assert not is_compatible(Tuple[Employee], Tuple[Manager])
        # And pairwise.
        assert is_compatible(Tuple[Manager, Manager], Tuple[Employee, Employee])
        assert not is_compatible(Tuple[Employee, Employee],
                                 Tuple[Manager, Employee])
        # And using ellipsis.
        assert is_compatible(Tuple[Manager, ...], Tuple[Employee, ...])
        assert not is_compatible(Tuple[Employee, ...], Tuple[Manager, ...])

    def test_covariance_sequence(self):
        # Check covariance for Sequence (which is just a generic class
        # for this purpose, but using a covariant type variable).
        assert is_compatible(typing.Sequence[Manager], typing.Sequence[Employee])
        assert not is_compatible(typing.Sequence[Employee],
                                 typing.Sequence[Manager])

    def test_covariance_mapping(self):
        # Ditto for Mapping (covariant in the value, invariant in the key).
        assert is_compatible(typing.Mapping[Employee, Manager],
                             typing.Mapping[Employee, Employee])
        assert not is_compatible(typing.Mapping[Manager, Employee],
                                 typing.Mapping[Employee, Employee])
        assert not is_compatible(typing.Mapping[Employee, Manager],
                                 typing.Mapping[Manager, Manager])
        assert not is_compatible(typing.Mapping[Manager, Employee],
                                 typing.Mapping[Manager, Manager])


class CastTests(TestCase):

    def test_basics(self):
        assert cast(int, 42) == 42
        assert cast(float, 42) == 42
        assert type(cast(float, 42)) is int
        assert cast(Any, 42) == 42
        assert cast(list, 42) == 42
        assert cast(Union[str, float], 42) == 42
        assert cast(AnyStr, 42) == 42
        assert cast(None, 42) == 42

    def test_errors(self):
        # Bogus calls are not expected to fail.
        cast(42, 42)
        cast('hello', 42)


class ForwardRefTests(TestCase):

    def test_basics(self):

        class Node(Generic[T]):

            def __init__(self, label: T):
                self.label = label
                self.left = self.right = None

            def add_both(self,
                         left: 'Optional[Node[T]]',
                         right: 'Node[T]' = None,
                         stuff: int = None,
                         blah=None):
                self.left = left
                self.right = right

            def add_left(self, node: Optional['Node[T]']):
                self.add_both(node, None)

            def add_right(self, node: 'Node[T]' = None):
                self.add_both(None, node)

        t = Node[int]
        both_hints = get_type_hints(t.add_both, globals(), locals())
        assert both_hints['left'] == both_hints['right'] == Optional[Node[T]]
        assert both_hints['stuff'] == Optional[int]
        assert 'blah' not in both_hints

        left_hints = get_type_hints(t.add_left, globals(), locals())
        assert left_hints['node'] == Optional[Node[T]]

        right_hints = get_type_hints(t.add_right, globals(), locals())
        assert right_hints['node'] == Optional[Node[T]]

    def test_forwardref_instance_type_error(self):
        fr = typing._ForwardRef('int')
        with self.assertRaises(TypeError):
            isinstance(42, fr)

    def test_union_forward(self):

        def foo(a: Union['T']):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': Union[T]})

    def test_tuple_forward(self):

        def foo(a: Tuple['T']):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': Tuple[T]})

    def test_callable_forward(self):

        def foo(a: Callable[['T'], 'T']):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': Callable[[T], T]})

    def test_callable_with_ellipsis_forward(self):

        def foo(a: 'Callable[..., T]'):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': Callable[..., T]})

    def test_syntax_error(self):

        with self.assertRaises(SyntaxError):
            Generic['/T']

    def test_delayed_syntax_error(self):

        def foo(a: 'Node[T'):
            pass

        with self.assertRaises(SyntaxError):
            get_type_hints(foo)

    def test_type_error(self):

        def foo(a: Tuple['42']):
            pass

        with self.assertRaises(TypeError):
            get_type_hints(foo)

    def test_name_error(self):

        def foo(a: 'Noode[T]'):
            pass

        with self.assertRaises(NameError):
            get_type_hints(foo, locals())

    def test_no_type_check(self):

        @no_type_check
        def foo(a: 'whatevers') -> {}:
            pass

        th = get_type_hints(foo)
        self.assertEqual(th, {})

    def test_no_type_check_class(self):

        @no_type_check
        class C:
            def foo(a: 'whatevers') -> {}:
                pass

        cth = get_type_hints(C.foo)
        self.assertEqual(cth, {})
        ith = get_type_hints(C().foo)
        self.assertEqual(ith, {})

    def test_meta_no_type_check(self):

        @no_type_check_decorator
        def magic_decorator(deco):
            return deco

        self.assertEqual(magic_decorator.__name__, 'magic_decorator')

        @magic_decorator
        def foo(a: 'whatevers') -> {}:
            pass

        @magic_decorator
        class C:
            def foo(a: 'whatevers') -> {}:
                pass

        self.assertEqual(foo.__name__, 'foo')
        th = get_type_hints(foo)
        self.assertEqual(th, {})
        cth = get_type_hints(C.foo)
        self.assertEqual(cth, {})
        ith = get_type_hints(C().foo)
        self.assertEqual(ith, {})

    def test_default_globals(self):
        code = ("class C:\n"
                "    def foo(self, a: 'C') -> 'D': pass\n"
                "class D:\n"
                "    def bar(self, b: 'D') -> C: pass\n"
                )
        ns = {}
        exec(code, ns)
        hints = get_type_hints(ns['C'].foo)
        assert hints == {'a': ns['C'], 'return': ns['D']}


class OverloadTests(TestCase):

    def test_overload_exists(self):
        from typing import overload

    def test_overload_fails(self):
        from typing import overload

        with self.assertRaises(RuntimeError):

            @overload
            def blah():
                pass

            blah()

    def test_overload_succeeds(self):
        from typing import overload

        @overload
        def blah():
            pass

        def blah():
            pass

        blah()


PY35 = sys.version_info[:2] >= (3, 5)

PY35_TESTS = """
import asyncio

T_a = TypeVar('T')

class AwaitableWrapper(typing.Awaitable[T_a]):

    def __init__(self, value):
        self.value = value

    def __await__(self) -> typing.Iterator[T_a]:
        yield
        return self.value

class AsyncIteratorWrapper(typing.AsyncIterator[T_a]):

    def __init__(self, value: typing.Iterable[T_a]):
        self.value = value

    def __aiter__(self) -> typing.AsyncIterator[T_a]:
        return self

    @asyncio.coroutine
    def __anext__(self) -> T_a:
        data = yield from self.value
        if data:
            return data
        else:
            raise StopAsyncIteration
"""

if PY35:
    exec(PY35_TESTS)


class CollectionsAbcTests(TestCase):

    def test_hashable(self):
        assert isinstance(42, typing.Hashable)
        assert not isinstance([], typing.Hashable)

    def test_iterable(self):
        assert isinstance([], typing.Iterable)
        # Due to ABC caching, the second time takes a separate code
        # path and could fail.  So call this a few times.
        assert isinstance([], typing.Iterable)
        assert isinstance([], typing.Iterable)
        assert not isinstance([], typing.Iterable[int])
        assert not isinstance(42, typing.Iterable)
        # Just in case, also test issubclass() a few times.
        assert issubclass(list, typing.Iterable)
        assert issubclass(list, typing.Iterable)
        assert is_compatible(list, typing.Iterable)
        assert not issubclass(list, typing.Iterable[int])
        assert is_compatible(list, typing.Iterable[int])
        assert not is_compatible(int, typing.Iterable[int])
        assert issubclass(tuple, typing.Sequence)
        assert is_compatible(tuple, typing.Sequence)
        assert not issubclass(tuple, typing.Sequence[int])
        assert is_compatible(tuple, typing.Sequence[int])

    def test_iterator(self):
        it = iter([])
        assert isinstance(it, typing.Iterator)
        assert not isinstance(it, typing.Iterator[int])
        assert not isinstance(42, typing.Iterator)
        assert is_compatible(type(it), typing.Iterator)
        assert is_compatible(type(it), typing.Iterator[int])
        assert not is_compatible(int, typing.Iterator[int])

    @skipUnless(PY35, 'Python 3.5 required')
    def test_awaitable(self):
        ns = {}
        exec(
            "async def foo() -> typing.Awaitable[int]:\n"
            "    return await AwaitableWrapper(42)\n",
            globals(), ns)
        foo = ns['foo']
        g = foo()
        assert isinstance(g, typing.Awaitable)
        assert not isinstance(foo, typing.Awaitable)
        assert is_compatible(type(g), typing.Awaitable[int])
        assert not is_compatible(type(foo), typing.Awaitable[int])
        assert not issubclass(typing.Awaitable[Manager],
                              typing.Awaitable[Employee])
        assert is_compatible(typing.Awaitable[Manager],
                             typing.Awaitable[Employee])
        assert not is_compatible(typing.Awaitable[Employee],
                                 typing.Awaitable[Manager])
        g.send(None)  # Run foo() till completion, to avoid warning.

    @skipUnless(PY35, 'Python 3.5 required')
    def test_async_iterable(self):
        base_it = range(10)  # type: Iterator[int]
        it = AsyncIteratorWrapper(base_it)
        assert isinstance(it, typing.AsyncIterable)
        assert isinstance(it, typing.AsyncIterable)
        assert is_compatible(typing.AsyncIterable[Manager],
                             typing.AsyncIterable[Employee])
        assert not isinstance(42, typing.AsyncIterable)

    @skipUnless(PY35, 'Python 3.5 required')
    def test_async_iterator(self):
        base_it = range(10)  # type: Iterator[int]
        it = AsyncIteratorWrapper(base_it)
        assert isinstance(it, typing.AsyncIterator)
        assert is_compatible(typing.AsyncIterator[Manager],
                             typing.AsyncIterator[Employee])
        assert not isinstance(42, typing.AsyncIterator)

    def test_sized(self):
        assert isinstance([], typing.Sized)
        assert not isinstance(42, typing.Sized)

    def test_container(self):
        assert isinstance([], typing.Container)
        assert not isinstance(42, typing.Container)

    def test_abstractset(self):
        assert isinstance(set(), typing.AbstractSet)
        assert not isinstance(42, typing.AbstractSet)

    def test_mutableset(self):
        assert isinstance(set(), typing.MutableSet)
        assert not isinstance(frozenset(), typing.MutableSet)

    def test_mapping(self):
        assert isinstance({}, typing.Mapping)
        assert not isinstance(42, typing.Mapping)

    def test_mutablemapping(self):
        assert isinstance({}, typing.MutableMapping)
        assert not isinstance(42, typing.MutableMapping)

    def test_sequence(self):
        assert isinstance([], typing.Sequence)
        assert not isinstance(42, typing.Sequence)

    def test_mutablesequence(self):
        assert isinstance([], typing.MutableSequence)
        assert not isinstance((), typing.MutableSequence)

    def test_bytestring(self):
        assert isinstance(b'', typing.ByteString)
        assert isinstance(bytearray(b''), typing.ByteString)

    def test_list(self):
        assert issubclass(list, typing.List)
        assert is_compatible(list, typing.List)

    def test_set(self):
        assert issubclass(set, typing.Set)
        assert not issubclass(frozenset, typing.Set)
        assert not is_compatible(frozenset, typing.Set)

    def test_frozenset(self):
        assert is_compatible(frozenset, typing.FrozenSet)
        assert not issubclass(set, typing.FrozenSet)
        assert not is_compatible(set, typing.FrozenSet)

    def test_dict(self):
        assert issubclass(dict, typing.Dict)

    def test_no_list_instantiation(self):
        with self.assertRaises(TypeError):
            typing.List()
        with self.assertRaises(TypeError):
            typing.List[T]()
        with self.assertRaises(TypeError):
            typing.List[int]()

    def test_list_subclass(self):

        class MyList(typing.List[int]):
            pass

        a = MyList()
        assert isinstance(a, MyList)
        assert isinstance(a, typing.Sequence)
        assert isinstance(a, collections.Sequence)

        assert issubclass(MyList, list)
        assert is_compatible(MyList, list)
        assert not is_compatible(list, MyList)

    def test_no_dict_instantiation(self):
        with self.assertRaises(TypeError):
            typing.Dict()
        with self.assertRaises(TypeError):
            typing.Dict[KT, VT]()
        with self.assertRaises(TypeError):
            typing.Dict[str, int]()

    def test_dict_subclass(self):

        class MyDict(typing.Dict[str, int]):
            pass

        d = MyDict()
        assert isinstance(d, MyDict)
        assert isinstance(d, typing.MutableMapping)
        assert isinstance(d, collections.MutableMapping)

        assert issubclass(MyDict, dict)
        assert is_compatible(MyDict, dict)
        assert not is_compatible(dict, MyDict)

    def test_no_defaultdict_instantiation(self):
        with self.assertRaises(TypeError):
            typing.DefaultDict()
        with self.assertRaises(TypeError):
            typing.DefaultDict[KT, VT]()
        with self.assertRaises(TypeError):
            typing.DefaultDict[str, int]()

    def test_defaultdict_subclass(self):

        class MyDefDict(typing.DefaultDict[str, int]):
            pass

        dd = MyDefDict()
        assert isinstance(dd, MyDefDict)

        assert issubclass(MyDefDict, collections.defaultdict)
        assert not is_compatible(collections.defaultdict, MyDefDict)

    def test_no_set_instantiation(self):
        with self.assertRaises(TypeError):
            typing.Set()
        with self.assertRaises(TypeError):
            typing.Set[T]()
        with self.assertRaises(TypeError):
            typing.Set[int]()

    def test_set_subclass_instantiation(self):

        class MySet(typing.Set[int]):
            pass

        d = MySet()
        assert isinstance(d, MySet)

    def test_no_frozenset_instantiation(self):
        with self.assertRaises(TypeError):
            typing.FrozenSet()
        with self.assertRaises(TypeError):
            typing.FrozenSet[T]()
        with self.assertRaises(TypeError):
            typing.FrozenSet[int]()

    def test_frozenset_subclass_instantiation(self):

        class MyFrozenSet(typing.FrozenSet[int]):
            pass

        d = MyFrozenSet()
        assert isinstance(d, MyFrozenSet)

    def test_no_tuple_instantiation(self):
        with self.assertRaises(TypeError):
            Tuple()
        with self.assertRaises(TypeError):
            Tuple[T]()
        with self.assertRaises(TypeError):
            Tuple[int]()

    def test_generator(self):
        def foo():
            yield 42
        g = foo()
        assert issubclass(type(g), typing.Generator)
        assert not issubclass(int, typing.Generator)
        assert is_compatible(typing.Generator[Manager, Employee, Manager],
                             typing.Generator[Employee, Manager, Employee])
        assert not is_compatible(typing.Generator[Manager, Manager, Manager],
                                 typing.Generator[Employee, Employee, Employee])

    def test_no_generator_instantiation(self):
        with self.assertRaises(TypeError):
            typing.Generator()
        with self.assertRaises(TypeError):
            typing.Generator[T, T, T]()
        with self.assertRaises(TypeError):
            typing.Generator[int, int, int]()

    def test_subclassing(self):

        class MMA(typing.MutableMapping):
            pass

        with self.assertRaises(TypeError):  # It's abstract
            MMA()

        class MMC(MMA):
            def __iter__(self): ...
            def __len__(self): return 0
            def __getitem__(self, name): ...
            def __setitem__(self, name, value): ...
            def __delitem__(self, name): ...

        assert len(MMC()) == 0
        assert callable(MMC.update)
        assert isinstance(MMC(), typing.Mapping)

        class MMB(typing.MutableMapping[KT, VT]):
            def __iter__(self): ...
            def __len__(self): return 0
            def __getitem__(self, name): ...
            def __setitem__(self, name, value): ...
            def __delitem__(self, name): ...

        assert len(MMB()) == 0
        assert len(MMB[str, str]()) == 0
        assert len(MMB[KT, VT]()) == 0
        assert isinstance(MMB[KT, VT](), typing.Mapping)
        assert isinstance(MMB[KT, VT](), collections.Mapping)

        assert not issubclass(dict, MMA)
        assert not issubclass(dict, MMB)
        assert not is_compatible(dict, MMA)
        assert not is_compatible(dict, MMB)

        assert issubclass(MMA, typing.Mapping)
        assert issubclass(MMB, typing.Mapping)
        assert issubclass(MMC, typing.Mapping)
        assert issubclass(MMA, collections.Mapping)
        assert issubclass(MMB, collections.Mapping)
        assert issubclass(MMC, collections.Mapping)
        assert is_compatible(MMC, typing.Mapping)
        assert is_compatible(MMC, collections.Mapping)

        assert issubclass(MMB[str, str], typing.Mapping)
        assert is_compatible(MMB[str, str], typing.Mapping)

        assert issubclass(MMC, MMA)
        assert is_compatible(MMC, MMA)

        assert not issubclass(MMA, typing.Mapping[str, str])
        assert not issubclass(MMB, typing.Mapping[str, str])

        class I(typing.Iterable): ...
        assert not issubclass(list, I)

        class G(typing.Generator[int, int, int]): ...
        def g(): yield 0
        assert issubclass(G, typing.Generator)
        assert issubclass(G, typing.Iterable)
        if hasattr(collections, 'Generator'):
            assert issubclass(G, collections.Generator)
        assert issubclass(G, collections.Iterable)
        assert not issubclass(type(g), G)

    def test_subclassing_subclasshook(self):

        class Base:
            @classmethod
            def __subclasshook__(cls, other):
                if other.__name__ == 'Foo':
                    return True
                else:
                    return False

        class C(Base, typing.Iterable): ...
        class Foo: ...

        assert issubclass(Foo, C)

    def test_subclassing_register(self):

        class A(typing.Container): ...
        class B(A): ...

        class C: ...
        A.register(C)
        assert is_compatible(C, A)
        assert not is_compatible(C, B)

        class D: ...
        B.register(D)
        assert is_compatible(D, A)
        assert is_compatible(D, B)

        class M(): ...
        collections.MutableMapping.register(M)
        assert issubclass(M, typing.Mapping)

    def test_collections_as_base(self):

        class M(collections.Mapping): ...
        assert issubclass(M, typing.Mapping)
        assert issubclass(M, typing.Iterable)

        class S(collections.MutableSequence): ...
        assert issubclass(S, typing.MutableSequence)
        assert issubclass(S, typing.Iterable)

        class I(collections.Iterable): ...
        assert issubclass(I, typing.Iterable)

        class A(collections.Mapping, metaclass=abc.ABCMeta): ...
        class B: ...
        A.register(B)
        assert issubclass(B, typing.Mapping)


class OtherABCTests(TestCase):

    @skipUnless(hasattr(typing, 'ContextManager'),
                'requires typing.ContextManager')
    def test_contextmanager(self):
        @contextlib.contextmanager
        def manager():
            yield 42

        cm = manager()
        assert isinstance(cm, typing.ContextManager)
        assert isinstance(cm, typing.ContextManager[int])
        assert not isinstance(42, typing.ContextManager)


class NamedTupleTests(TestCase):

    def test_basics(self):
        Emp = NamedTuple('Emp', [('name', str), ('id', int)])
        assert issubclass(Emp, tuple)
        joe = Emp('Joe', 42)
        jim = Emp(name='Jim', id=1)
        assert isinstance(joe, Emp)
        assert isinstance(joe, tuple)
        assert joe.name == 'Joe'
        assert joe.id == 42
        assert jim.name == 'Jim'
        assert jim.id == 1
        assert Emp.__name__ == 'Emp'
        assert Emp._fields == ('name', 'id')
        assert Emp._field_types == dict(name=str, id=int)

    def test_pickle(self):
        global Emp  # pickle wants to reference the class by name
        Emp = NamedTuple('Emp', [('name', str), ('id', int)])
        jane = Emp('jane', 37)
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            z = pickle.dumps(jane, proto)
            jane2 = pickle.loads(z)
            self.assertEqual(jane2, jane)


class IOTests(TestCase):

    def test_io(self):

        def stuff(a: IO) -> AnyStr:
            return a.readline()

        a = stuff.__annotations__['a']
        assert a.__parameters__ == (AnyStr,)

    def test_textio(self):

        def stuff(a: TextIO) -> str:
            return a.readline()

        a = stuff.__annotations__['a']
        assert a.__parameters__ == ()

    def test_binaryio(self):

        def stuff(a: BinaryIO) -> bytes:
            return a.readline()

        a = stuff.__annotations__['a']
        assert a.__parameters__ == ()

    def test_io_submodule(self):
        from typing.io import IO, TextIO, BinaryIO, __all__, __name__
        assert IO is typing.IO
        assert TextIO is typing.TextIO
        assert BinaryIO is typing.BinaryIO
        assert set(__all__) == set(['IO', 'TextIO', 'BinaryIO'])
        assert __name__ == 'typing.io'


class RETests(TestCase):
    # Much of this is really testing _TypeAlias.

    def test_basics(self):
        pat = re.compile('[a-z]+', re.I)
        assert is_compatible(pat.__class__, Pattern)
        assert is_compatible(type(pat), Pattern)
        assert is_compatible(type(pat), Pattern[str])

        mat = pat.search('12345abcde.....')
        assert is_compatible(mat.__class__, Match)
        assert is_compatible(mat.__class__, Match[str])
        assert is_compatible(mat.__class__, Match[bytes])  # Sad but true.
        assert is_compatible(type(mat), Match)
        assert is_compatible(type(mat), Match[str])

        p = Pattern[Union[str, bytes]]
        assert is_compatible(Pattern[str], Pattern)
        assert is_compatible(Pattern[str], p)

        m = Match[Union[bytes, str]]
        assert is_compatible(Match[bytes], Match)
        assert is_compatible(Match[bytes], m)

    def test_errors(self):
        with self.assertRaises(TypeError):
            # Doesn't fit AnyStr.
            Pattern[int]
        with self.assertRaises(TypeError):
            # Can't change type vars?
            Match[T]
        m = Match[Union[str, bytes]]
        with self.assertRaises(TypeError):
            # Too complicated?
            m[str]
        with self.assertRaises(TypeError):
            # We don't support isinstance().
            isinstance(42, Pattern)
        with self.assertRaises(TypeError):
            # We don't support isinstance().
            isinstance(42, Pattern[str])

    def test_repr(self):
        assert repr(Pattern) == 'Pattern[~AnyStr]'
        assert repr(Pattern[str]) == 'Pattern[str]'
        assert repr(Pattern[bytes]) == 'Pattern[bytes]'
        assert repr(Match) == 'Match[~AnyStr]'
        assert repr(Match[str]) == 'Match[str]'
        assert repr(Match[bytes]) == 'Match[bytes]'

    def test_re_submodule(self):
        from typing.re import Match, Pattern, __all__, __name__
        assert Match is typing.Match
        assert Pattern is typing.Pattern
        assert set(__all__) == set(['Match', 'Pattern'])
        assert __name__ == 'typing.re'

    def test_cannot_subclass(self):
        with self.assertRaises(TypeError) as ex:

            class A(typing.Match):
                pass

        assert str(ex.exception) == "A type alias cannot be subclassed"


class AllTests(TestCase):
    """Tests for __all__."""

    def test_all(self):
        from typing import __all__ as a
        # Just spot-check the first and last of every category.
        assert 'AbstractSet' in a
        assert 'ValuesView' in a
        assert 'cast' in a
        assert 'overload' in a
        if hasattr(contextlib, 'AbstractContextManager'):
            assert 'ContextManager' in a
        # Check that io and re are not exported.
        assert 'io' not in a
        assert 're' not in a
        # Spot-check that stdlib modules aren't exported.
        assert 'os' not in a
        assert 'sys' not in a
        # Check that Text is defined.
        assert 'Text' in a


if __name__ == '__main__':
    main()
