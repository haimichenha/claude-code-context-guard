import csv
from decimal import InvalidOperation
from pathlib import Path
import tempfile
import unittest
from summarize import summarize

class HostAcceptance(unittest.TestCase):
    def test_original_fixture(self):
        r=summarize(Path(__file__).with_name('orders.csv'))
        self.assertEqual(r['row_count'],3);self.assertEqual(str(r['total_qty']),'6');self.assertEqual(r['total_amount'],'43.95')
    def test_invalid_fields(self):
        for qty,price in [('1.5','2'),('-1','2'),('NaN','2'),('Infinity','2'),('1','-2'),('1','NaN'),('1','Infinity')]:
            with self.subTest(qty=qty,price=price),tempfile.TemporaryDirectory() as d:
                p=Path(d)/'input.csv'
                with p.open('w',newline='',encoding='utf-8') as f:
                    w=csv.writer(f);w.writerow(['item','qty','unit_price']);w.writerow(['fixture',qty,price])
                with self.assertRaises((ValueError,InvalidOperation)):
                    summarize(p)
if __name__=='__main__':unittest.main()
