from pathlib import Path

import numpy as np
import pytest
from ase.calculators.subprocesscalculator import (NamedPackedCalculator,
                                                  MPICommand)
from ase.calculators.emt import EMT
from ase.build import molecule, bulk
from ase.optimize import BFGS


def get_fmax(forces):
    return max((forces**2).sum(axis=1)**0.5)


@pytest.fixture
def atoms():
    atoms = bulk('Au') * (2, 2, 2)
    atoms.rattle(stdev=0.05, seed=2)
    return atoms


def assert_results_equal_to_ordinary_emt(atoms):
    atoms1 = atoms.copy()
    atoms1.calc = EMT()

    assert (atoms.get_potential_energy()
            == pytest.approx(atoms1.get_potential_energy()))
    assert atoms.get_forces() == pytest.approx(atoms1.get_forces())
    assert atoms.get_stress() == pytest.approx(atoms1.get_stress())


def test_subprocess_calculator_emt(atoms):
    pack = NamedPackedCalculator('emt')

    with pack.calculator() as atoms.calc:
        assert_results_equal_to_ordinary_emt(atoms)
        atoms.rattle(stdev=0.1, seed=17)
        atoms.cell[1, 2] += 0.1
        atoms.pbc[0] = False
        assert_results_equal_to_ordinary_emt(atoms)

    # As before, but the results are supposedly cached:
    assert_results_equal_to_ordinary_emt(atoms)


def test_subprocess_calculator_optimize(atoms):
    pack = NamedPackedCalculator('emt')
    opt = BFGS(atoms)

    fmax = 0.05
    with pack.calculator() as atoms.calc:
        fmax_start = get_fmax(atoms.get_forces())
        assert fmax_start > fmax
        opt.run(fmax=fmax)
        atoms.get_stress()

    fmax_now = get_fmax(atoms.get_forces())
    assert fmax_now < fmax
    assert_results_equal_to_ordinary_emt(atoms)


@pytest.mark.calculator_lite
@pytest.mark.calculator('gpaw')
def test_subprocess_calculator_mpi(factory):
    pytest.importorskip('mpi4py')
    atoms = molecule('H2', vacuum=2.0)
    atoms.pbc = 1
    nbands = 2
    pack = NamedPackedCalculator('gpaw', dict(mode='lcao',
                                              nbands=nbands))
    mpi = MPICommand.parallel(2)
    with pack.calculator(mpi) as calc:
        atoms.calc = calc
        atoms.get_potential_energy()
        gpaw = calc.backend()
        assert gpaw.get_number_of_bands() == nbands

        gpw = Path('dumpfile.gpw')
        gpaw.write(gpw)
        assert gpw.exists()

        nt_g = gpaw.get_pseudo_density(spin=0)
        assert isinstance(nt_g, np.ndarray)
        assert nt_g.dtype == float
        assert all(dim > 10 for dim in nt_g.shape)
