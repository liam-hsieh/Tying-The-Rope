
input_path='C:\Users\liam\Documents\MATLAB\Tying The Rope\Inputs\';
input_file_name='examples.xlsx';

[~, product,~]     = xlsread([input_path, input_file_name], 'BasicInfo','A:A');
[~, site,~]        = xlsread([input_path, input_file_name], 'BasicInfo','B:B');
[~, quarter,~]     = xlsread([input_path, input_file_name], 'BasicInfo','C:C');

                BasicInfo = struct('product', {product} ...
                                   ,'site', {transpose(site)} ...
                                   ,'quarter', {transpose(quarter)}...
                                   );