from antar_engine import chart
c = chart.calculate_chart('1972-08-10', '07:20', 28.6139, 77.2090, 5.5)
print("Lagna:", c['lagna']['sign'], c['lagna']['degree'])
