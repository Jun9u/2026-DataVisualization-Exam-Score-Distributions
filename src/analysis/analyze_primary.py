"""Reproduce the primary descriptive analysis from verified CSAT/CPA tables."""
import csv
import re
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data/processed/primary"
OUT = ROOT / "results/primary"
CS, CPA = "수능 본시험", "공인회계사 1차"
CONCORDANCE = INPUT / "csat.csv"
CPA_FILE = INPUT / "cpa.csv"
ORDER = ["영어","한국사","경영학","경제원론","상법","기업법","세법개론","회계학","전과목 평균"]
SPLIT, EXT = "개편 후 별도", "2025 추가 비교"
FIXED, RECENT = [2020,2021,2022], [2023,2024]


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows):
    def format_value(x):
        if isinstance(x, Fraction):
            return f"{float(x):.8f}"
        return x
    with (OUT / (name + ".csv")).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k:format_value(v) for k,v in row.items()})


def status(exam, year):
    if year==2025:
        return EXT if exam==CS else SPLIT
    return "최근 공통" if year in RECENT else "과거 기준"


def fixed_mean(series, years):
    return mean(series[y] for y in years) if all(y in series for y in years) else None


def comparison_windows(exam, past):
    """Keep the common five-year comparison; add 2025 only for the unchanged CSAT scale."""
    windows = [("고정 과거", FIXED, RECENT), ("전체 과거", past, RECENT)]
    if exam == CS:
        windows += [("고정 과거·2025 포함", FIXED, [2023, 2024, 2025]),
                    ("전체 과거·2025 포함", past, [2023, 2024, 2025])]
    return windows


def consecutive_changes(series, years):
    return {y: series[y] - series[y-1] for y in years if y-1 in series}


def read_sources():
    groups = defaultdict(list)
    for r in read(CONCORDANCE):
        year = int(r["시행연도"])
        assert (r["시험"], r["단계"]) == ("수능", "본시험")
        assert r["과목_모집단"] in ("영어", "한국사")
        subject = r["과목_모집단"]
        assert r["회차_학년도"]==f"{year+1}학년도"
        order = int(r["원표내_순서"])
        grade, left, right = map(int,re.fullmatch(r"(\d)등급 \((\d+)~(\d+)점\)",r["구간"]).groups())
        assert order==grade
        groups[CS,subject,year].append((order,left,right,"이하",r["구간"],int(r["구간인원"]),int(r["분모"]),r["출처ID"],None))
    for r in read(CPA_FILE):
        year = int(r["시행연도"])
        left = int(r["하한_이상"])
        top = r["상한_미만"]==""
        right = 100 if top else int(r["상한_미만"])
        label = "90점 이상" if top else f"{left}–{right}점 미만"
        groups[CPA,r["과목_평균"],year].append((left//10+1,left,right,"이하" if top else "미만",label,int(r["구간인원"]),int(r["응시자"]),r["원자료"],int(r["하한이상_누적인원"])))
    return groups


def thresholds(exam,subject):
    if exam==CPA:
        return [(80,"80점 이상","대표"),(70,"70점 이상","보조"),(90,"90점 이상","보조")]
    return [(90 if subject=="영어" else 40,"1등급","대표"),(80 if subject=="영어" else 35,"1–2등급","보조")]


def exam_key(key):
    exam,sub,year = key
    return (exam!=CS,ORDER.index(sub),year)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    groups = read_sources()
    qa = {(r["과목"], int(r["시행연도"])): int(r["대조값"])
          for r in read(INPUT / "denominators.csv")}
    assert len(qa)==19
    audits, bins, levels, reform_bins, reform_high = [], [], [], [], []
    series, bin_series = defaultdict(dict),defaultdict(dict)
    for key in sorted(groups,key=exam_key):
        exam,sub,y = key
        es = status(exam,y)
        roles = "공식 전과목 평균·보조" if sub=="전과목 평균" else "과목"
        items = sorted(groups[key])
        orders, lows, highs, bounds, labels, counts, totals, ids, cum = zip(*items)
        n = totals[0]
        assert len(set(totals))==len(set(ids))==1 and n>0
        assert len(items)==(9 if exam==CS else 10) and list(orders)==list(range(1,len(items)+1))
        assert all(c>=0 for c in counts) and sum(counts)==n
        if exam==CPA:
            assert list(lows)==list(range(0,100,10)) and all(sum(counts[i:])==v for i,v in enumerate(cum))
            denom_ref,ref_n="공식 표 0점 이상 누계",cum[0]
        else:
            assert sorted(zip(lows,highs))[0][0] == 0 and all(a[1]+1==b[0] for a,b in zip(sorted(zip(lows,highs)),sorted(zip(lows,highs))[1:]))
            denom_ref,ref_n="품질 검토서의 별도 발표 과목별 응시인원",qa[sub,y]
        assert ref_n==n
        base=dict(시험=exam,과목=sub,시행연도=y,분석구분=es)
        audits.append(dict(**base,지표역할=roles,사용파일="data/processed/primary/"+str((CONCORDANCE if exam==CS else CPA_FILE).relative_to(INPUT)),출처=ids[0],
            분모=n,구간수=len(items),구간인원합=sum(counts),차이=sum(counts)-n,대조기준=denom_ref,대조값=ref_n,
            검산="일치",제외_별도_사유={SPLIT:"배점·과목 개편, 개편 전 비교 미산입",EXT:"공통 기간 외 2025 포함 비교에 사용"}.get(es,"")))
        for order,left,right,bound,label,c,denom,src,_ in items:
            share = Fraction(100*c,n)
            bucket = dict(**base,구간순서=order,구간=label,하한_이상=left,상한=right,상한조건=bound,인원=c,분모=n,비율_pct=share,출처=src)
            (reform_bins if es==SPLIT else bins).append(bucket)
            if es!=SPLIT:
                bin_series[exam,sub,order,label][y]=share
        for cut,label,typ in thresholds(exam,sub):
            c=sum(row[5] for row in items if row[1]>=cut)
            if exam==CPA:
                assert c==cum[lows.index(cut)]
            share=Fraction(100*c,n)
            row=dict(**base,지표=label,지표구분=typ,기준점_이상=cut,인원=c,분모=n,비중_pct=share)
            if es==SPLIT:
                reform_high.append(row)
            else:
                levels.append(row)
                series[exam,sub,label][y]=share
    periods,history=[],[]
    for (exam,sub,label),s in series.items():
        cut,_,typ=next(t for t in thresholds(exam,sub) if t[1]==label)
        past=sorted(y for y in s if y<=2022)
        hist=consecutive_changes(s, past)
        assert len(past) >= 5 and len(hist) >= 4
        extreme=max(map(abs,hist.values()))
        abs_pairs=", ".join(f"{y-1}→{y}" for y,d in hist.items() if abs(d)==extreme)
        base=dict(시험=exam,과목=sub,지표=label,지표구분=typ)
        for y in sorted(y for y in s if y >= 2023 and y-1 in s):
            d=s[y]-s[y-1]
            history.append(dict(**base,시행연도=y,전년차_pp=d,과거_연속쌍수=len(hist),과거최소_pp=min(hist.values()),과거최대_pp=max(hist.values()),
                과거최대절대변동_pp=extreme,해당_과거쌍=abs_pairs,최근절대변동_pp=abs(d),
                절대크기판정="초과" if abs(d)>extreme else ("동일" if abs(d)==extreme else "이내"),
                부호포함범위="기존 최솟값 미만" if d<min(hist.values()) else ("기존 최댓값 초과" if d>max(hist.values()) else "범위 내")))
        for tag,years,recent_years in comparison_windows(exam, past):
            old=fixed_mean(s,years)
            recent=fixed_mean(s,recent_years)
            periods.append(dict(**base,비교=tag,과거연도=",".join(map(str,years)),최근연도=",".join(map(str,recent_years)),
                과거연도수=len(years),최근연도수=len(recent_years),과거평균_pct=old,최근평균_pct=recent,차이_pp=recent-old if None not in (old,recent) else None,
                산출상태="산출" if None not in (old,recent) else "필요 연도 누락"))
    for row in levels:
        series_ = series[row["시험"],row["과목"],row["지표"]]
        y=row["시행연도"]
        row["전년차_pp"]=series_[y]-series_[y-1] if y-1 in series_ else None
        row["전년차_상태"]="연속연도" if y-1 in series_ else "첫 관측 또는 전년 자료 없음"
    band_changes=[]
    for (exam,sub,order,label),s in bin_series.items():
        past=sorted(y for y in s if y<=2022)
        for tag,years,recent_years in comparison_windows(exam, past):
            old=fixed_mean(s,years)
            new=fixed_mean(s,recent_years)
            band_changes.append(dict(시험=exam,과목=sub,구간순서=order,구간=label,비교=tag,
                과거연도=",".join(map(str,years)),최근연도=",".join(map(str,recent_years)),
                과거평균_pct=old,최근평균_pct=new,차이_pp=new-old if None not in (old,new) else None,
                연간_2023_pp=s[2023]-s[2022],연간_2024_pp=s[2024]-s[2023],
                연간_2025_pp=s[2025]-s[2024] if 2025 in s else None))
    grouped=defaultdict(list)
    for r in band_changes:
        grouped[r["시험"],r["과목"],r["비교"]].append(r)
    displacements=[]
    for (exam,sub,tag),rows in grouped.items():
        vals=[r["차이_pp"] for r in rows]
        assert sum(vals)==0
        hi=max(rows,key=lambda r:r["차이_pp"])
        lo=min(rows,key=lambda r:r["차이_pp"])
        displacements.append(dict(시험=exam,과목=sub,비교=tag,과거연도=rows[0]["과거연도"],최근연도=rows[0]["최근연도"],
            구간비중절대차합_절반_pp=sum(abs(d) for d in vals)/2,
            최대증가구간=hi["구간"],증가_pp=hi["차이_pp"],최대감소구간=lo["구간"],감소_pp=lo["차이_pp"]))
    # Annual TVD compares complete distributions with identical boundaries.
    shapes=defaultdict(dict)
    for (exam,sub,order,label),s in bin_series.items():
        for y,value in s.items():
            shapes[exam,sub].setdefault(y,{})[(order,label)]=value
    tvd_annual=[]
    for (exam,sub),ys in shapes.items():
        changes={}
        for y in sorted(ys):
            if y-1 not in ys:
                continue
            left,right=ys[y-1],ys[y]
            assert left.keys()==right.keys() and sum(left.values())==sum(right.values())==100
            changes[y]=sum(abs(right[k]-left[k]) for k in left)/2
        past={y:v for y,v in changes.items() if y<=2022}
        assert len(past)>=4
        historical_max=max(past.values())
        for y,v in changes.items():
            assert 0<=v<=100
            tvd_annual.append(dict(시험=exam,과목=sub,이전연도=y-1,시행연도=y,
                전체분포변화량_pp=v,과거_연속쌍수=len(past),과거최대_pp=historical_max,
                과거최대_연도쌍=", ".join(f"{k-1}→{k}" for k,x in past.items() if x==historical_max),
                판정="과거 관측" if y<=2022 else ("초과" if v>historical_max else "동일" if v==historical_max else "이내")))
    assert len(audits)==79 and len(levels)==200 and len(history)==48 and len(periods)==52
    assert len(bins)==711 and len(reform_bins)==60 and len(reform_high)==18
    assert len(displacements)==20 and len(tvd_annual)==65
    for name,table in [("01_audit",audits),("02_annual",levels),("02_recent_vs_history",history),
                       ("03_periods",periods),("04_distribution",bins),("04_band_changes",band_changes),
                       ("04_distribution_summary",displacements),("04_annual_tvd",tvd_annual),("05_cpa2025_levels",reform_high),("05_cpa2025_distribution",reform_bins)]:
        write(name,table)
    print("검산 완료:",len(audits),"개 분포,",len(levels),"개 연도별 지표,",len(bins)+len(reform_bins),"개 사용 구간")


if __name__=="__main__":
    main()
