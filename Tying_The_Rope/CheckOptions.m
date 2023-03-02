function Options = CheckOptions(obj, ref_mat)
%% ref_mat: matrix withich requires to check the avalaible options
%% Options: 2D array with three columns
%% col1: preduct index; col2: site index; col3: option type 1 or 2 (primary or secondary)

[prod_ix, site_ix] = find(ref_mat==1);
mix_idx = @(i,j) [i,j];
checked = mix_idx(prod_ix, site_ix);

primary_options = setdiff(obj.Options.primary, checked, 'row');
secondary_options = setdiff(obj.Options.secondary, checked, 'row');
primary_options(:, 3) = ones(size(primary_options,1),1);
secondary_options(:, 3) = ones(size(secondary_options,1),1)*2;
Options = [primary_options; secondary_options];
end

