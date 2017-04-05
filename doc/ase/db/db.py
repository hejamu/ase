# creates: ase-db.txt, ase-db-long.txt, known-keys.csv
import ase.db
c = ase.db.connect('abc.db', append=False)

from ase import Atoms
from ase.calculators.emt import EMT
h2 = Atoms('H2', [(0, 0, 0), (0, 0, 0.7)])
h2.calc = EMT()
h2.get_forces()

c.write(h2, relaxed=False)

from ase.optimize import BFGS
BFGS(h2).run(fmax=0.01)
c.write(h2, relaxed=True, data={'abc': [1, 2, 3]})

for d in c.select('molecule'):
    print(d.forces[0, 2], d.relaxed)

h = Atoms('H')
h.calc = EMT()
h.get_potential_energy()
c.write(h)

import subprocess
with open('ase db.txt', 'w') as fd:
    fd.write('$ ase db abc.db\n')
    output = subprocess.check_output(['ase', 'db', 'abc.db'])
    fd.write(output.decode())
with open('ase-db-long.txt', 'w') as fd:
    fd.write('$ ase db abc.db relaxed=1 -l\n')
    output = subprocess.check_output(['ase', 'db', 'abc.db', 'relaxed=1', '-l'])
    fd.write(output.decode())

row = c.get(relaxed=1, calculator='emt')
for key in row:
    print('{0:22}: {1}'.format(key, row[key]))

print(row.data.abc)

e2 = row.energy
e1 = c.get(H=1).energy
ae = 2 * e1 - e2
print(ae)

id = c.get(relaxed=1).id
c.update(id, atomization_energy=ae)

del c[c.get(relaxed=0).id]

from ase.db.app import default_key_descriptions
with open('known-keys.csv', 'w') as fd:
    print('key,short description,long description,type,unit', file=fd)
    for key, (short, long, type, unit) in default_key_descriptions.items():
        if unit == '|e|':
            unit = '\|e|'
        print('{},{},{},{},{}'.format(key, short, long, type, unit), file=fd)
