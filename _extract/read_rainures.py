import openpyxl
wb = openpyxl.load_workbook(r'DROSIM_SA61-_#Simulation drop test avion complet.xlsm', data_only=True)
ws = wb['MLG']
lines = []
for r in [47, 48, 49, 50]:
    lines.append('row ' + str(r) + ' ' + str([ws.cell(r, c).value for c in range(16, 30)]))
open(r'_extract\rainures_out.txt', 'w').write('\n'.join(lines))
print('done')
