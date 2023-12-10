function TestifyProposedMatrix(obj, varargin)
% Testify the proposed matrix and update Qmat, Stat, and Progress
%% mat_name: name of proposed matrix, if empty, use default one (the last link added during optimization)

% Set default values
keep_raw = obj.Setting.keep_raw.other_quarters;
name_of_proposed_mat = 'proposed';
qmat_str = fieldnames(obj.Qmat);
s_qmat = qmat_str(contains(qmat_str, 'link'));
f = @(c) str2num(c(5:end));
mat_name = ['link' num2str(max(arrayfun(@(s) f(char(s)), s_qmat)))];

% Check the number of input arguments
if nargin>3
    error('too many input args!');
elseif nargin==3
    % Check the validity of mat_name and keep_raw
    if (islogical(varargin{2}) && (sum(contains(qmat_str, varargin{1}))>0) && ischar(varargin{1}))
        keep_raw = varargin{2};
        mat_name = varargin{1};
    else
        error('check mat_name does exist in Qmat and use logical value for keeping raw');
    end
elseif nargin==2
    mat_name = varargin{1};
end

mat_name = char(mat_name); %name of proposed link

%========= update Qmat, Stat============
obj.Qmat.(name_of_proposed_mat)=obj.Qmat.(mat_name);
[obj.Stat.(name_of_proposed_mat)] = obj.Stat.(mat_name); %Stat is a 1 by many struct, so scalar structure required

%update Progress
mat_name_str = string({obj.Progress{:,1}});
[res, mat_ix, ~] = find(contains(mat_name_str, mat_name));
if sum(size(res))==2
    obj.Progress{mat_ix,1} = name_of_proposed_mat;
else
    error(max(arrayfun(@(s) f1(char(s)), s_qmat)))
end

qmat_str = string([fieldnames(obj.Qmat)]);
participants = transpose((~strncmp(qmat_str, 'link', 4)).*(qmat_str~='temp').*(qmat_str~='exclustion'));
participants = qmat_str(logical(participants));
num_participants = size(participants, 1);

for q=1:obj.Pars.num_quarter
    if q ==obj.Setting.Ref_quarter, continue;,end;
    
    for i=1:num_participants
        RS = obj.Evaluate(participants(i), q, keep_raw);
    end
end



