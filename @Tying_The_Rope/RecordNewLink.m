function RecordNewLink(obj, BestLink, Ref_Qmat_name, added_Qmat_name)
    %% BestLink: result of the next best link
    %% Ref_Qmat_name: baseline matrix name
    %% added_Qmat_name: matrix name for the new link
    
    % Check if added_Qmat_name is not empty
    if ~isempty(added_Qmat_name)
        BestLink{1} = added_Qmat_name;
    end
    
    % Check if Ref_Qmat_name is not empty
    if ~isempty(Ref_Qmat_name)
        % Create a matrix before adding the link
        obj.Qmat.(added_Qmat_name) = obj.Qmat.(Ref_Qmat_name); % create matrix before adding link
        obj.Qmat.(added_Qmat_name)(BestLink{3}, BestLink{4}) = 1; %renew the matrix by adding the best link if necessary
    end
    
    % Update the Progress
    obj.Progress = [obj.Progress; BestLink];
end