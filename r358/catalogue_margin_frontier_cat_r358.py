#!/usr/bin/env python3
"""CAT-R358: prioritized MANUAL OCR-confusion review queue; never merge refs or infer makers."""
from __future__ import annotations
import csv, hashlib, json
from decimal import Decimal, InvalidOperation
from pathlib import Path
R=Path(__file__).resolve().parent
ZERO=Decimal('0')


def rank_groups(groups):
    rows=[]
    for g in groups:
        edges=g.get('edges',[])
        if len(g['members'])<2 or not edges: raise ValueError('empty_group')
        margins=[]
        for edge in edges:
            try: margin=Decimal(edge['extra_uncertainty_mm_REPORT_ONLY'])
            except (InvalidOperation,ValueError) as exc:raise ValueError('bad_margin') from exc
            if not margin.is_finite() or margin<ZERO:raise ValueError('bad_margin')
            margins.append(margin)
        nearest=min(margins)
        if nearest==ZERO:level='P0 - recouvrement théorique'
        elif nearest<=Decimal('0.1'):level='P1 - marge <= 0,1 mm'
        elif nearest<=Decimal('0.5'):level='P2 - marge <= 0,5 mm'
        else:level='P3 - examen différé'
        rows.append({'members':g['members'],'references':' / '.join(g['members']),
          'member_count':len(g['members']), 'ocr_edges':len(edges),
          'closest_extra_uncertainty_mm':str(nearest),
          'level':level, 'unknown_manufacturer_some':bool(g['unknown_manufacturer_some']),
          'action':'vérifier mesures et graphie sur clés réelles ; confirmer fabricant si manquant',
          'manual_review_only':True,'approved_alias':False,'threshold_change':False})
    rows.sort(key=lambda row:(Decimal(row['closest_extra_uncertainty_mm']),
                             -row['member_count'],row['references']))
    return rows


def run():
    source=json.loads((R/'CAT_R356_OCR_COMPONENTS.json').read_text(encoding='utf-8'))
    rows=rank_groups(source['components'])
    priority=[r for r in rows if r['level'].startswith(('P0','P1','P2'))]
    by_level={p:sum(r['level'].startswith(p) for r in rows) for p in ('P0','P1','P2','P3')}
    def reject(fixture):
        try:rank_groups(fixture)
        except ValueError:return True
        return False
    fixtures={
      'negative_uncertainty_rejected':reject([{'members':['A','B'],'edges':[{'extra_uncertainty_mm_REPORT_ONLY':'-0.1'}],'unknown_manufacturer_some':False}]),
      'nan_uncertainty_rejected':reject([{'members':['A','B'],'edges':[{'extra_uncertainty_mm_REPORT_ONLY':'NaN'}],'unknown_manufacturer_some':False}]),
      'missing_edges_rejected':reject([{'members':['A','B'],'edges':[],'unknown_manufacturer_some':False}]),
      'sorted_deterministically':rows==rank_groups(list(reversed(source['components']))),
    }
    checks={
      'R356_source_valid':source['ok'] and source['edges']==68,
      '64_groups_130_exact_refs':len(rows)==64 and len({n for g in source['components'] for n in g['members']})==130,
      'all_68_edges_retained':sum(r['ocr_edges'] for r in rows)==68,
      'two_original_overlap_groups':by_level['P0']==2 and [r['references'] for r in rows[:2]]==['VI4 / VL4','VI4R / VL4R'],
      'two_high_risk_triples':set(r['references'] for r in rows if r['member_count']==3)=={'CIL1 / CLI1 / CLL1','KF1 / KFI / KFL'},
      'all_review_only_no_alias':all(r['manual_review_only'] and not r['approved_alias'] and not r['threshold_change'] for r in rows),
      'original_fragments_present':len(source['canonical_sha256'])==10 and all((R.parent/'app/catalogue/v3'/fn).is_file() for fn in source['canonical_sha256']),
      'canonical_sha256_identical':all(hashlib.sha256((R.parent/'app/catalogue/v3'/fn).read_bytes()).hexdigest()==dig for fn,dig in source['canonical_sha256'].items()),
      'all_fixtures':all(fixtures.values()),
    }
    output={'schema':'bres-cat-r358-manual-ocr-review-queue-v1','milestone':'CAT-R358','parent':'CAT-R357',
      'scope':'theoretical ordering only; margins do not represent observed Samsung accuracy',
      'canonical_sha256':source['canonical_sha256'], 'source_graph_sha256':hashlib.sha256((R/'CAT_R356_OCR_COMPONENTS.json').read_bytes()).hexdigest(),
      'groups':len(rows),'references':130,'edges':68,'priority_distribution':by_level,
      'priority_up_to_half_mm':len(priority),'queue':rows,'fixtures':fixtures,'checks':checks,
      'manufacturer_inferred':False,'OCR_rules_changed':False,'physical_measurements_used':False,
      'ok':all(checks.values())}
    (R/'CAT_R358_DIMENSION_PRIORITY.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (R/'CAT_R358_DIMENSION_PRIORITY.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f)
        writer.writerow(['priorite','references','minimum_incertitude_supplementaire_theorique_mm','taille_groupe','nombre_liens_OCR','fabricant_manquant_dans_un_lien','validation'])
        for row in rows:writer.writerow([row['level'],row['references'],row['closest_extra_uncertainty_mm'],row['member_count'],row['ocr_edges'],row['unknown_manufacturer_some'],'A VERIFIER MANUELLEMENT'])
    (R/'CAT_R358_DIMENSION_PRIORITY.txt').write_text(
      f"CAT-R358 : {len(rows)} groupes, 130 références, 68 liens OCR ; {len(priority)} groupes avec marge <=0,5 mm.\n"
      f"Priorités : {by_level}. Les marges sont théoriques et non des mesures Samsung.\n"
      'Aucune équivalence, fabricant ou règle de reconnaissance n\'a été activé.\n',encoding='utf-8')
    print(json.dumps({'ok':output['ok'],'checks':len(checks),'distribution':by_level,'priority_half_mm':len(priority),'fixtures':len(fixtures)}))
    return 0 if output['ok'] else 1
if __name__=='__main__':raise SystemExit(run())