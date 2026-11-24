import numpy as np
import pytest

from cclab_preproc.exp00_segments import build


def make_run(tmp_path, n_on=2):
    run = tmp_path / "Movie_g0"
    (run / "Movie_g0_imec0").mkdir(parents=True)
    d = np.zeros((1000, 9), dtype=np.int16)
    for k in range(n_on):
        d[100 + 300 * k : 110 + 300 * k, 8] |= 1 << 2  # on
        d[300 + 300 * k : 310 + 300 * k, 8] |= 1 << 0  # off
    d.tofile(run / "Movie_g0_t0.nidq.bin")
    (run / "Movie_g0_t0.nidq.meta").write_text("niSampRate=100\nnSavedChans=9\nfirstSample=1000\n")
    (run / "Movie_g0_imec0" / "Movie_g0_t0.imec0.ap.meta").write_text("imSampRate=30000\nfirstSample=300000\n")
    log = tmp_path / "event_log.csv"
    log.write_text(
        "timestamp_local,event,trial,segment,detail\n"
        'x,PairSelected,1,NaN,"A=a.mp4;B=b.mp4;sameCategory=1"\n'
        'x,SegmentOn,1,1,"movie=A;ttl_ms=50"\nx,SegmentOff,1,1,"movie=A;ttl_ms=50"\n'
        'x,SegmentOn,1,1,"movie=B;ttl_ms=50"\nx,SegmentOff,1,1,"movie=B;ttl_ms=50"\n'
    )
    return run, log


def test_labels_and_clock(tmp_path):
    df = build(*make_run(tmp_path))
    assert df.movie.tolist() == ["A", "B"] and df.video.tolist() == ["a.mp4", "b.mp4"]
    assert df.t_on_s.tolist() == [1.0, 4.0] and df.t_off_s.tolist() == [3.0, 6.0]
    assert df.on_ap_sample.tolist() == [30000, 120000]  # both streams started together


def test_count_mismatch_stops(tmp_path):
    with pytest.raises(SystemExit):
        build(*make_run(tmp_path, n_on=3))
