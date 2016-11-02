"""test_filtertools.py
Test code for pyret's filtertools module.
(C) 2016 The Baccus Lab.
"""

import numpy as np
import pytest

from pyret import filtertools as flt
from pyret.stimulustools import slicestim

import utils

def test_ste():
    """Test computing a spike-triggered ensemble."""
    np.random.seed(0)
    time = np.arange(100)
    spikes = np.array((30, 70))
    stimulus = np.random.randn(100,)
    filter_length = 5

    ste = flt.ste(time, stimulus, spikes, filter_length)
    for ix in spikes:
        assert np.allclose(stimulus[ix - filter_length : ix], next(ste))

def test_sta():
    """Test computing a spike-triggered average."""
    np.random.seed(0)
    time = np.arange(100)
    spikes = np.array((0, 30, 70))
    stimulus = np.random.randn(100,)
    filter_length = 5

    sta, tax = flt.sta(time, stimulus, spikes, filter_length)
    tmp = np.zeros(sta.shape)
    for ix in spikes[1:]: # Should ignore first spike, comes before filter_length frames
        tmp += stimulus[ix - filter_length : ix]
    tmp /= len(spikes)

    assert np.allclose(tmp, sta)
    assert np.allclose(tax, np.arange(filter_length))

def test_empty_sta():
    """Test that an empty with no spikes returns an array of nans"""
    np.random.seed(0)
    time = np.arange(100)
    spikes = np.array(())
    stimulus = np.random.randn(100,)
    filter_length = 5
    
    sta, _ = flt.sta(time, stimulus, spikes, filter_length)
    assert np.all(np.isnan(sta))

def test_stc():
    """Test computation of a spike-triggered covariance matrix."""
    np.random.seed(0)

    # random spike times an white noise stimulus, so STC should be close to identity
    npoints = 100000
    nspikes = 1000
    time = np.arange(npoints)
    spikes = np.random.randint(0, npoints, (nspikes,))
    stimulus = np.random.randn(npoints,)
    filter_length = 10

    tmp = flt.stc(time, stimulus, spikes, filter_length)
    atol = 0.1
    assert np.allclose(tmp, np.eye(filter_length), atol=atol)

def test_empty_stc():
    """Test STC with no spike returns array of nans"""
    np.random.seed(0)

    # random spike times an white noise stimulus, so STC should be close to identity
    npoints = 100
    nspikes = 0
    time = np.arange(npoints)
    spikes = np.random.randint(0, npoints, (nspikes,))
    stimulus = np.random.randn(npoints,)
    filter_length = 10

    tmp = flt.stc(time, stimulus, spikes, filter_length)
    assert np.all(np.isnan(tmp))


def test_decompose():
    """Tests computing a rank-1 approximation to a filter.
    Note that this tests both filtertools.decompose() and filtertools.lowranksta().
    """
    np.random.seed(0)
    filter_length = 50
    nx, ny = 10, 10
    temporal, spatial, true_filter = utils.create_spatiotemporal_filter(nx, ny, filter_length)

    noise_std = 0.01
    true_filter += np.random.randn(*true_filter.shape) * noise_std

    s, t = flt.decompose(true_filter)

    tol = 0.1
    assert np.allclose(temporal, t, atol=tol)
    assert np.allclose(spatial, s, atol=tol)

def test_filterpeak():
    """Test finding the maximal point in a 3D filter"""
    arr = np.zeros((5, 2, 2))
    true_index = 7
    arr.flat[true_index] = -1
    true_indices = np.unravel_index(true_index, arr.shape)

    idx, sidx, tidx  = flt.filterpeak(arr)
    assert true_index == idx
    assert true_indices[0] == tidx
    assert np.all(true_indices[1:] == sidx)

def test_cutout():
    """Test cutting out a small tube through a 3D spatiotemporal filter"""
    np.random.seed(0)
    chunk = np.random.randn(4, 2, 2)
    arr = np.pad(chunk, ((0, 0), (1, 1), (1, 1)), 'constant', constant_values=0)
    cutout = flt.cutout(arr, (2, 2), width=1)
    assert np.allclose(cutout, chunk)

def test_cutout_peak():
    """Test that the `filtertools.cutout()` method correctly uses the filter peak."""
    chunk = np.zeros((4, 2, 2))
    chunk[2, 1, 1] = 1
    arr = np.pad(chunk, ((0, 0), (1, 1), (1, 1)), 'constant', constant_values=0)
    cutout = flt.cutout(arr, width=1)
    assert np.allclose(cutout, chunk)

def test_cutout_raises():
    """Test cutout() raises an exception when the index argument does not have two elements."""
    with pytest.raises(ValueError):
        flt.cutout(np.zeros((10, 10, 10)), (1,))

def test_normalize_spatial():
    """Test normalizing a noisy filter."""
    np.random.seed(0)
    filter_length = 100
    nx, ny = 10, 10
    true_filter = utils.create_spatiotemporal_filter(nx, ny, filter_length)[1]
    noise_std = 0.01
    noisy_filter = -(true_filter + 1.0 + np.random.randn(*true_filter.shape) * 0.01)

    normalized = flt.normalize_spatial(noisy_filter)
    normalized /= np.linalg.norm(normalized)

    atol = 0.1
    assert np.allclose(normalized, true_filter, atol=atol)

def test_rfsize():
    np.random.seed(0)
    filter_length = 100
    nx, ny = 10, 10
    true_filter = utils.create_spatiotemporal_filter(nx, ny, filter_length)[1]
    
    xsize, ysize = flt.rfsize(true_filter, 1., 1.)
    assert np.allclose(xsize, 3., 0.1) # 1 SD is about 3 units
    assert np.allclose(ysize, 3., 0.1)

def test_linear_prediction_1d():
    """Test method for computing linear prediction from a 
    filter to a one-dimensional stimulus.
    """
    np.random.seed(0)
    filt = np.random.randn(100,)
    stim = np.random.randn(1000,)
    pred = flt.linear_prediction(filt, stim)

    sl = slicestim(stim, filt.shape[0])
    assert np.allclose(filt.reshape(1, -1).dot(sl), pred)

def test_linear_prediction_nd():
    """Test method for computing linear prediction from a 
    filter to a multi-dimensional stimulus.
    """
    np.random.seed(0)
    for ndim in range(2, 4):
        filt = np.random.randn(100, *((10,) * ndim))
        stim = np.random.randn(1000, *((10,) * ndim))
        pred = flt.linear_prediction(filt, stim)

        sl = slicestim(stim, filt.shape[0])
        tmp = np.zeros(sl.shape[1])
        filt_reshape = filt.reshape(1, -1)
        for i in range(tmp.size):
            tmp[i] = filt_reshape.dot(sl[:, i, :].reshape(-1, 1))

        assert np.allclose(tmp, pred)

def test_linear_prediction_raises():
    """Test raising ValueErrors with incorrect inputs"""
    np.random.seed(0)
    with pytest.raises(ValueError):
        flt.linear_prediction(np.random.randn(10,), np.random.randn(10,2))
    with pytest.raises(ValueError):
        flt.linear_prediction(np.random.randn(10, 2), np.random.randn(10, 3))

def test_revcorr_raises():
    """Test raising ValueErrors with incorrect inputs"""
    np.random.seed(0)
    with pytest.raises(ValueError):
        flt.revcorr(np.random.randn(10,), np.random.randn(10,2), 2)
    with pytest.raises(ValueError):
        flt.revcorr(np.random.randn(10, 2), np.random.randn(10, 3), 2)

def test_revcorr_1d():
    """Test computation of a 1D linear filter by reverse correlation"""
    np.random.seed(0)

    # Create fake filter, 100 time points
    filter_length = 100
    true_filter = utils.create_temporal_filter(filter_length)

    # Compute linear response
    stim_length = 10000
    stimulus = np.random.randn(stim_length,)
    response = flt.linear_prediction(true_filter, stimulus)

    # Reverse correlation
    filt = flt.revcorr(response, stimulus, filter_length)
    filt /= np.linalg.norm(filt)
    tol = 0.1
    assert np.allclose(true_filter, filt, atol=tol)


def test_revcorr_nd():
    np.random.seed(0)

    """Test computation of 3D linear filter by reverse correlation"""
    # Create fake filter
    filter_length = 100
    nx, ny = 10, 10
    true_filter = utils.create_spatiotemporal_filter(nx, ny, filter_length)[-1]

    # Compute linear response
    stim_length = 10000
    stimulus = np.random.randn(stim_length, nx, ny)
    response = flt.linear_prediction(true_filter, stimulus)

    # Reverse correlation
    filt = flt.revcorr(response, stimulus, filter_length)
    filt /= np.linalg.norm(filt)
    tol = 0.1
    assert np.allclose(true_filter, filt, atol=tol)
