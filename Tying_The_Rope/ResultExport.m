function ResultExport(obj)
%% export the simulation result from properties

filename = 'Outputs.xlsx';

if exist(fullfile(obj.Dir.output, filename))==2, delete(fullfile(obj.Dir.output, filename));, end;

%export Progress
%=================

progress = obj.Progress;
for i=2:size(progress,1)
    if progress{i,3}==0
        progress{i,3}='';
    else
        progress{i,3}=obj.BasicInfo.product(progress{i,3});
    end
    
    if progress{i,4}==0
        progress{i,4}='';
    else
        progress{i,4}=obj.BasicInfo.site(progress{i,4});
    end
end

sheetname = 'LinkAddProgress';
row_label = [];
column_label = [];
obj.Export2Excel(progress, obj.Dir.output, filename, sheetname, row_label, column_label);



%export Metrics at Recommended Qual
mat_name = 'proposed';
num_prod = size(obj.BasicInfo.product, 1);
num_site = size(obj.BasicInfo.site, 2);

SL_label = ['' '' 'Overall SL'];
prod_SL_label = [repmat('Product SL', num_prod, 1) obj.BasicInfo.product];
site_exp_label = [repmat('Expected Site Utilization', num_site, 1) transpose(obj.BasicInfo.site)];
site_P10_label = [repmat('P10 of Site Utilization', num_site, 1) transpose(obj.BasicInfo.site)];
row_label = [SL_label ; prod_SL_label; site_exp_label; site_P10_label];

values = zeros(site(row_label, 1), obj.Pars.num_quarter);

for q=1:obj.Pars.num_quarter
    values(1,q) = obj.Stat(q).(mat_name).SL.mean;
    values(2:1+num_prod, q) = obj.Stat(q).(mat_name).SL_prod.mean;
    values(2+num_prod: 1+num_prod+num_site, q) = obj.Stat(q).(mat_name).U_site.mean;
    values(2+num_prod + num_site: 1+num_prod+num_site*2, q) = obj.Stat(q).(mat_name).U_site.P10;
end

values = [row_label values];

sheetname = 'Metrics under Recomended Qual';
column_label = ['' '' '' '' obj.BasicInfo.quarter];
row_label = [];
obj.Export2Excel(values, obj.Dir.output, filename, sheetname, row_label, column_label);


%export expected loading

num_site = size(obj.BasicInfo.site, 2);
empty_row = [repmat(' ', 1, num_site +1)];
full_stack = empty_row;
for q = 1:obj.Pars.num_quarter
    column_label = [obj.BasicInfo.quarter(q) obj.BasicInfo.site];
    values = [obj.BasicInfo.product obj.Stat(q).proposed.Var_x.mean];
    values = [column_label; values; empty_row];
    
    full_stack = [full_stack; values];
end

sheetname = 'Expected Loading';
row_label = [];
column_label = [];
obj.Export2Excel(full_stack, obj.Dir.output, filename, sheetname, row_label, column_label);


sheetname = 'Qual matrix';
row_label = obj.BasicInfo.product;
column_label = obj.BasicInfo.site;
obj.Export2Excel(obj.Qmat.proposed, obj.Dir.output, filename, sheetname, row_label, column_label);



