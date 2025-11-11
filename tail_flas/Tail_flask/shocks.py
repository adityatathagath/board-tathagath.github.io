import pandas as pd

shocks = pd.read_excel(r'shocks.xlsx')
template = pd.read_excel(r'template.xlsx')

template['MappedTenor'] = template['Tenor'].replace('1B', 'ON')

shock_cols = [c for c in shocks.columns if c != 'IssuerCountry']
shocks_long = shocks.melt(id_vars='IssuerCountry', value_vars=shock_cols,
                          var_name='Tenor', value_name='Shocks')

merged = template.merge(shocks_long,
                        left_on=['IssuerCountry', 'MappedTenor'],
                        right_on=['IssuerCountry', 'Tenor'],
                        how='left')

final = merged[['IssuerCountry', 'Tenor_x', 'Shocks']].rename(columns={'Tenor_x': 'Tenor'})
final.to_excel('template_filled.xlsx', index=False)
