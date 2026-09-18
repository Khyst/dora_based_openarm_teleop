# Copyright 2026 Enactic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from openarm_driver.base_safety import (
    CheckResult,
    Checker,
    NullChecker,
    CompositeChecker,
    ConditionalChecker,
    CachedChecker,
)


class DummyChecker(Checker):
    def __init__(
        self,
        is_safe=True,
        force_stop=False,
        fixed_joint_positions=None,
    ):
        self.is_safe = is_safe
        self.force_stop = force_stop
        self.fixed_joint_positions = fixed_joint_positions

    def check(self, joint_positions, **kwargs):
        return CheckResult(
            is_safe=self.is_safe,
            force_stop=self.force_stop,
            fixed_joint_positions=(
                joint_positions
                if self.fixed_joint_positions is None
                else self.fixed_joint_positions
            ),
        )


def test_base_checker():
    checker = DummyChecker()
    result = checker.check([])
    assert result.is_safe


def test_null_checker():
    checker = NullChecker()
    result = checker.check([])
    assert result.is_safe


def test_composite_checker_none_stop():
    checker = CompositeChecker(
        [
            DummyChecker(),
            DummyChecker(
                is_safe=False,
                fixed_joint_positions=[1],
            ),
            DummyChecker(),
        ]
    )
    result = checker.check([0])
    assert not result.is_safe
    assert not result.force_stop
    assert result.fixed_joint_positions == [1]


def test_composite_checker_force_stop_halfway():
    checker = CompositeChecker(
        [
            DummyChecker(),
            DummyChecker(
                is_safe=False,
                fixed_joint_positions=[1],
            ),
            DummyChecker(is_safe=False, force_stop=True),
            DummyChecker(
                is_safe=False,
                fixed_joint_positions=[2],
            ),
        ]
    )
    result = checker.check([0])
    assert not result.is_safe
    assert result.force_stop
    assert result.fixed_joint_positions == [1]


def test_conditional_checker():
    def condition(joint_positions, arg):
        return arg == 0

    checker = ConditionalChecker(DummyChecker(is_safe=False), condition)

    result = checker.check([], arg=0)
    assert not result.is_safe
    assert result.message == ""

    result = checker.check([], arg=1)
    assert result.is_safe
    assert result.message == checker.skip_message


def test_cached_checker():
    def condition(joint_positions, arg):
        return arg == 0

    checker = CachedChecker(
        ConditionalChecker(DummyChecker(is_safe=False), condition),
        tolerance=1.0,
    )

    result = checker.check([0], arg=1)
    assert result.is_safe

    # Cached result should be used.
    result = checker.check([0.5], arg=0)
    assert result.is_safe

    # The new check should be run.
    result = checker.check([3], arg=0)
    assert not result.is_safe
