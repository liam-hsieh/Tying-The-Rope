clear; clc;
clear global;

%tic;

TTR=Tying_The_Rope(0,20,100);
TTR.CreateRandDemand();
TTR.Optimize(2) %use quarter 2 as ref
TTR.TestifyProposedMatrix();
TTR.ResultExport();
t=toc;

%~ = TTR.ObserveLoading('plan', 4, 0.3, true); %mat_name, quarter, cov, export