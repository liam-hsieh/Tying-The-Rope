function ClearAddedLink(obj)

%======clean the progress==========
num_row = size(obj.Progress, 1);
if num_row > 1
    obj.Progress(2:num_row, :) = [];
end

%================clean Stat================
if isfield(obj.Stat,'proposed'), obj.Stat = rmfield(obj.Stat,'proposed');end
%if sum(contains(fieldnames(obj.Stat), 'link'))>0
if sum(cellfun(@(x) ~isempty(strfind(x, 'link')), fieldnames(obj.Stat))) > 0
    prefix = 'link';
    fn = fieldnames(obj.Stat);
    tf = strncmp(fn, prefix, length(prefix));
    obj.Stat = rmfield(obj.Stat, fn(tf));
end


%=========clean Qmat =======================
if isfield(obj.Qmat,'proposed'), obj.Stat = rmfield(obj.Qmat,'proposed');end
%if sum(contains(fieldnames(obj.Qmat), 'link'))>0
%search for the substring 'link' in the field names of obj.Qmat using the strfind function, and return the number of times it appears
if sum(cellfun(@(x) ~isempty(strfind(x, 'link')), fieldnames(obj.Qmat))) > 0
    prefix = 'link';
    fn = fieldnames(obj.Qmat);
    tf = strncmp(fn, prefix, length(prefix));
    obj.Qmat = rmfield(obj.Qmat, fn(tf));
end

%=========clean Recordset =======================
if isfield(obj.Recordset,'proposed'), obj.Stat = rmfield(obj.Recordset,'proposed');end
%if sum(contains(fieldnames(obj.Recordset), 'link'))>0
if sum(cellfun(@(x) ~isempty(strfind(x, 'link')), fieldnames(obj.Recordset))) > 0  
    prefix = 'link';
    fn = fieldnames(obj.Recordset);
    tf = strncmp(fn, prefix, length(prefix));
    obj.Recordset = rmfield(obj.Recordset, fn(tf));
end
