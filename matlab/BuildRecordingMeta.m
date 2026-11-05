function meta = BuildRecordingMeta(cfgOverride)
% BUILDRECORDINGMETA  Assemble ONE standardized .mat per recording, per task,
% for any project in lab!
%
% Output: a single nested struct `meta` on a common neural clock (seconds):
%   meta.info    provenance + session metadata
%   meta.spikes  per-unit cluster metadata + spike-time cells (seconds)
%   meta.trials  one row per ATTEMPTED trial, aligned to the neural clock
%   meta.events  raw synced event streams (trial start / attempt, all codes)
%   meta.lfp     placeholder (will add once vFLIP2 is streamlined)
%
% REQUIRES readNPY (npy-matlab: https://github.com/kwikteam/npy-matlab) on the
% path. addpath it if you do not have it.
%
% HOW TO RUN
%   1) Edit the CONFIG block below (line 56), then press Run (F5).
%   2) Or pass a cfgOverride struct to change fields at call time (see below 
%   for detailed instructions).
%
%       THE cfgOverride INPUT (optional)
%   
%       cfgOverride is a struct whose fields REPLACE the matching defaults in the
%       CONFIG block. Only the fields you include are overridden; everything else
%       keeps its default. Call with no argument to use the defaults as written
%       below.
%
%       The point: reuse this one function across many recordings WITHOUT editing
%       the file each time - you pass in just what differs for a given session,
%       likely the date, spiking, event, and trial information.
%
%       Examples of usage:
%       1) -->    BuildRecordingMeta();                       % no input argument, use CONFIG defaults as-is
%
%       2)--->    cfg = struct();                             % override two fields only
%                 cfg.date         = '040825';
%                 cfg.behavior_mat = 'C:\...\040825_Vennie\MGSDiffDir\remgs.mat';
%                 BuildRecordingMeta(cfg);                    % date + behavior swapped, rest default
%
%       The idea is it will loop over sessions, build a small cfg (date, 
%       ks_dir, sync_events, behavior_mat, out_dir) from each session folder, 
%       and call BuildRecordingMeta(cfg) once per recording.
%
%       Valid override fields = any field set in the CONFIG block below
%       (subject, date, task, sampling_rate, lfp_fs, inclusion, code_start,
%       code_attempt, n_target_pos, ks_dir, sync_events, behavior_mat, out_dir).
%
%
%
% CONVENTIONS
%   - spike_times.npy are SAMPLES at sampling_rate (30 kHz) -> seconds = /sr
%   - sync_event_codes col 2 is MILLISECONDS on the neural clock -> /1000
%   - event code 4 = trial start, event code 1 = trial attempt (alignment)
%   - unit inclusion = KSLabel in {good, mua}
% -------------------------------------------------------------------------
%
%% ======================== ADD readNPY TO PATH ===========================

% EDIT: point this at your copy of npy-matlab
addpath('C:\Users\tphamel\Desktop\Taylor\WorkingMemory\Modules\npy-matlab-master\npy-matlab-master\npy-matlab')


%% ============================ CONFIG ====================================
cfg = struct();
cfg.subject       = 'Venni';
cfg.date          = '040825';            
cfg.task          = 'MGSDiffDir';        % task name
cfg.sampling_rate = 30000;               % Hz (spike / AP band)
cfg.lfp_fs        = 1250;                % Hz (for when LFP is added)
cfg.inclusion     = {'good','mua'};      % KSLabel groups to keep
cfg.code_start    = 4;                   % event code: trial start
cfg.code_attempt  = 1;                   % event code: trial attempt (alignment)
cfg.n_target_pos  = 8;                   % 8-direction MGS 
cfg.builder_version = 'm-1.0';         % recorded in meta.info (was read but never set)

cfg.ks_dir        = 'C:\Users\tphamel\Desktop\Taylor\WorkingMemory\MGSDiffDir\Neuropixel\040825_Vennie\MGS\neuro\MGS2_g0_imec0\curated\kilosort4';
cfg.sync_events   = 'C:\Users\tphamel\Desktop\Taylor\WorkingMemory\MGSDiffDir\Neuropixel\040825_Vennie\MGS\neuro\sync_event_codes.npy';
cfg.behavior_mat  = 'C:\Users\tphamel\Desktop\Taylor\WorkingMemory\MGSDiffDir\Neuropixel\040825_Vennie\MGS\matlab\remgs1';                  % '' = skip trials; else path to Results .mat / table
cfg.out_dir       = 'C:\Users\tphamel\Desktop\Taylor\WorkingMemory\MGSDiffDir\Neuropixel\040825_Vennie\MGS';
% =========================================================================

if nargin >= 1 && isstruct(cfgOverride)          % apply any overrides
    for f = fieldnames(cfgOverride)', cfg.(f{1}) = cfgOverride.(f{1}); end
end
if exist('readNPY','file') ~= 2
    error(['readNPY not found on the path. Get npy-matlab from ' ...
           'https://github.com/kwikteam/npy-matlab and addpath it. ' ...
           ]);
end

% ---- Build the pieces ----------------------------------------------------
[spikes, nUnits]          = loadSpikes(cfg);
[events, attemptTimes]    = loadEvents(cfg);
if ~isempty(cfg.behavior_mat)
    trials = loadBehavior(cfg, attemptTimes);
else
    z = zeros(0,1);
    trials = struct('attempt_time',z,'trial_success',z,'target_group',z, ...
                    'x_sp',z,'y_sp',z,'reward_amount',z);
end

% ---- info / provenance ---------------------------------------------------
info.subject        = cfg.subject;
info.date           = cfg.date;
info.task           = cfg.task;
info.session_id     = sprintf('%s_%s_%s', cfg.subject, cfg.date, cfg.task);
info.sampling_rate  = cfg.sampling_rate;
info.lfp_fs         = cfg.lfp_fs;
info.timebase       = 'seconds, neural (Kilosort AP) clock';
info.unit_inclusion = ['KSLabel in {' strjoin(cfg.inclusion, ',') '}'];
info.n_units            = nUnits;
info.n_trials_attempted = numel(trials.trial_success);
info.n_trials_success   = sum(trials.trial_success == 1);
info.source_files   = struct('ks_dir',cfg.ks_dir,'sync_events',cfg.sync_events, ...
                             'behavior_mat',cfg.behavior_mat);
info.builder_version = cfg.builder_version;
info.built_on       = char(datetime('now'));
info.notes          = '';

% ---- lfp placeholder -----------------------------------------------------
lfp = struct('data',[],'fs',cfg.lfp_fs,'channel_map',[], ...
             'channel_positions',[],'status','not_yet_added');

meta = struct('info',info,'spikes',spikes,'trials',trials,'events',events,'lfp',lfp);

% ---- Save ----------------------------------------------------------------
outFile = fullfile(cfg.out_dir, [info.session_id '_meta.mat']);
save(outFile, 'meta');
fprintf('Built %s: %d units, %d attempted / %d success\nSaved -> %s\n', ...
        info.session_id, nUnits, info.n_trials_attempted, info.n_trials_success, outFile);
end

%% ========================= LOCAL FUNCTIONS ==============================
function [spikes, nUnits] = loadSpikes(cfg)
% Per-unit metadata + spike-time cells (seconds), for included units.
st = double(readNPY(fullfile(cfg.ks_dir,'spike_times.npy')));     % samples
sc = double(readNPY(fullfile(cfg.ks_dir,'spike_clusters.npy')));  % cluster id
ci = readtable(fullfile(cfg.ks_dir,'cluster_info.tsv'), ...
               'FileType','text','Delimiter','\t');

keep = ismember(ci.KSLabel, cfg.inclusion);
uid  = ci.cluster_id(keep);
nUnits = numel(uid);

% group spike times (seconds) per included unit, in cluster_ids order.
% Map each spike's cluster -> unit index (0 if excluded), then accumarray.
lut = zeros(max(sc)+1, 1);
lut(uid+1) = 1:nUnits;                     % +1 because ids are 0-based
uidx = lut(sc+1);                          % per-spike unit index (0 = drop)
m = uidx > 0;
cells = accumarray(uidx(m), st(m)/cfg.sampling_rate, [nUnits 1], @(x){sort(x)});

spikes.cluster_ids      = uid;
spikes.depths           = ci.depth(keep);
spikes.ch_best          = ci.ch(keep);
spikes.ks_labels        = ci.KSLabel(keep);        % cellstr
spikes.n_spikes         = ci.n_spikes(keep);
spikes.contam_pct       = ci.ContamPct(keep);
spikes.firing_rate      = ci.fr(keep);
spikes.spike_times_cell = cells;
end

function [events, attempt] = loadEvents(cfg)
% Trial-start / trial-attempt streams (seconds) + the full synced code stream.
sec   = double(readNPY(cfg.sync_events));   % (N,2) [code, time_ms]
codes = sec(:,1);
tsec  = sec(:,2) / 1000;                     % ms -> s
events.trial_start_times   = unique(tsec(codes == cfg.code_start));
events.trial_attempt_times = unique(tsec(codes == cfg.code_attempt));
events.event_codes         = codes;
events.event_times_s       = tsec;
attempt = events.trial_attempt_times;
end

function trials = loadBehavior(cfg, attemptTimes)
% Read the behavioral file, keep ATTEMPTED trials, align to neural attempt
% times, and compute target_group. Handles either a saved table OR a Results
% struct (labels/data), like the neuropixel-pipeline behavioral .mat.
%
S = load(cfg.behavior_mat);
fn = fieldnames(S);
Tb = [];
for i = 1:numel(fn)
    if istable(S.(fn{i})), Tb = S.(fn{i}); break; end
end
if isempty(Tb)                              % Results struct (labels + data)
    R = S.Results;
    labels = cellstr(string(R.labels(:)'));
    cols   = R.data(:)';                     % 1 x nVars cell, each nTrials x 1
    Tb = array2table([cols{:}], 'VariableNames', matlab.lang.makeValidName(labels));
end

att = Tb(Tb.TrialAttemp == 1, :);
if height(att) ~= numel(attemptTimes)
    error(['Alignment mismatch: %d attempted behavioral trials vs %d neural ' ...
           'attempt events. Inspect before trusting this session.'], ...
           height(att), numel(attemptTimes));
end

trials.attempt_time  = attemptTimes(:);
trials.trial_success = double(att.TrialSuccess);
trials.x_sp          = double(att.x_sp);
trials.y_sp          = double(att.y_sp);
trials.reward_amount = double(att.RewardAmount);
trials.target_group  = arrayfun(@(x,y) assignGroupMGS(x,y,cfg.n_target_pos), ...
                                trials.x_sp, trials.y_sp);
end

function g = assignGroupMGS(x, y, npos)
% Map a target (x,y) to a direction group 1..npos (from the notebook).
ang = round(rad2deg(atan2(y, x)));
if npos == 8
    keys = [45 0 -45 -90 -135 180 135 90];  vals = [1 2 3 4 5 6 7 8];
else
    keys = [45 0 -45 -135 180 135];         vals = [1 2 3 4 5 6];
end
d = abs(mod(ang - keys + 180, 360) - 180);   % circular nearest key
[~, k] = min(d);
g = vals(k);
end
